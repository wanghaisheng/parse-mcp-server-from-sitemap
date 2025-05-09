import os
import re
import csv
from datetime import datetime, timedelta

def get_id_files(result_dir, prefix="app_ids_", suffix=".txt"):
    files = []
    for fname in os.listdir(result_dir):
        if fname.startswith(prefix) and fname.endswith(suffix):
            files.append(fname)
    return sorted(files)

def extract_date_from_filename(filename, prefix="app_ids_", suffix=".txt"):
    date_str = filename[len(prefix):-len(suffix)]
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None

def load_ids_from_file(filepath):
    if not os.path.exists(filepath):
        return set()
    with open(filepath, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

def load_app_details_csv(filepath):
    details = {}
    if not os.path.exists(filepath):
        return details
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            details[row['id']] = row
    return details

def save_app_details_csv(details_list, filepath):
    if not details_list:
        return
    fieldnames = ['id', 'loc', 'lastmodified', 'added_date']
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in details_list:
            writer.writerow(row)

def analyze_period_ids(result_dir, period_days, today=None):
    if today is None:
        today = datetime.now()
    files = get_id_files(result_dir)
    period_start = today - timedelta(days=period_days)
    period_files = [f for f in files if extract_date_from_filename(f) and extract_date_from_filename(f) > period_start]
    all_ids = set()
    for fname in period_files:
        ids = load_ids_from_file(os.path.join(result_dir, fname))
        all_ids.update(ids)
    return all_ids, period_files

def generate_report(result_dir, period, period_days, report_prefix="report_"):
    today = datetime.now()
    ids, files = analyze_period_ids(result_dir, period_days, today)
    report_file = os.path.join(result_dir, f"{report_prefix}{period}_{today.strftime('%Y-%m-%d')}.txt")
    details_file = os.path.join(result_dir, "app_details.csv")
    details_map = load_app_details_csv(details_file)
    new_details = [details_map[app_id] for app_id in sorted(ids) if app_id in details_map]
    details_report_file = os.path.join(result_dir, f"{report_prefix}{period}_details_{today.strftime('%Y-%m-%d')}.csv")
    save_app_details_csv(new_details, details_report_file)
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"{period} 新增app数量: {len(ids)}\n")
        for app_id in sorted(ids):
            f.write(f"{app_id}\n")
        f.write(f"涉及文件: {', '.join(files)}\n")
    print(f"{period}报告已生成: {report_file}")
    print(f"{period}详情CSV已生成: {details_report_file}")

def main():
    data_dir = os.path.join(os.path.dirname(__file__), '../data')
    os.makedirs(data_dir, exist_ok=True)
    # 日报
    generate_report(data_dir, "daily", 1)
    # 周报
    generate_report(data_dir, "weekly", 7)
    # 月报
    generate_report(data_dir, "monthly", 30)

if __name__ == "__main__":
    main()
