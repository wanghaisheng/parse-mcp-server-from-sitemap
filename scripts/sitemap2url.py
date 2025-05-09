import requests
import gzip
import xml.etree.ElementTree as ET
from io import BytesIO
import logging
from datetime import datetime
import os
import csv
from collections import deque

def setup_logging(log_file="sitemap_collector.log"):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def fetch_xml(url):
    try:
        logging.info(f"Fetching XML: {url}")
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logging.error(f"Failed to fetch XML: {url}, error: {e}")
        return None

def fetch_gzip_xml(url):
    try:
        logging.info(f"Fetching GZipped XML: {url}")
        response = requests.get(url)
        response.raise_for_status()
        with gzip.GzipFile(fileobj=BytesIO(response.content)) as f:
            return f.read().decode('utf-8')
    except Exception as e:
        logging.error(f"Failed to fetch GZipped XML: {url}, error: {e}")
        return None

def extract_url_details_from_xml(xml_content):
    """
    提取每个<url>节点下的loc和lastmod，返回列表[{loc, lastmodified}]
    """
    try:
        root = ET.fromstring(xml_content)
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        details = []
        for url_elem in root.findall('.//ns:url', ns):
            loc_elem = url_elem.find('ns:loc', ns)
            lastmod_elem = url_elem.find('ns:lastmod', ns)
            loc = loc_elem.text if loc_elem is not None else None
            lastmod = lastmod_elem.text if lastmod_elem is not None else None
            if loc:
                details.append({'loc': loc, 'lastmodified': lastmod})
        return details
    except Exception as e:
        logging.error(f"XML parse error: {e}")
        return []

def extract_links_from_xml(xml_content, tag="loc"):
    try:
        root = ET.fromstring(xml_content)
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        return [elem.text for elem in root.findall(f".//ns:{tag}", ns)]
    except Exception as e:
        logging.error(f"XML parse error: {e}")
        return []

def is_gzip_url(url):
    return url.lower().endswith('.gz')

def is_xml_url(url):
    return url.lower().endswith('.xml')

def collect_all_url_details_from_sitemap(entry_url, max_depth=5, existing_url_date_map=None, today=None):
    """
    递归采集所有最终url的loc、lastmodified、首次添加日期。
    """
    visited = set()
    url_details = []
    queue = deque([(entry_url, 0)])
    if existing_url_date_map is None:
        existing_url_date_map = {}
    if today is None:
        today = datetime.now().strftime('%Y-%m-%d')
    while queue:
        url, depth = queue.popleft()
        if url in visited or depth > max_depth:
            continue
        visited.add(url)
        if is_gzip_url(url):
            xml_content = fetch_gzip_xml(url)
        else:
            xml_content = fetch_xml(url)
        if not xml_content:
            continue
        # 判断是 sitemap index 还是 urlset
        links = extract_links_from_xml(xml_content, tag="loc")
        # 如果有<url>节点，提取详情，否则递归
        if xml_content.find('<url') != -1:
            details = extract_url_details_from_xml(xml_content)
            for d in details:
                loc = d['loc']
                lastmod = d['lastmodified']
                add_date = existing_url_date_map.get(loc, today)
                url_details.append({'loc': loc, 'lastmodified': lastmod, 'added_date': add_date})
        elif links:
            for link in links:
                if is_xml_url(link) or is_gzip_url(link):
                    queue.append((link, depth+1))
    return url_details

def load_url_details_csv(file_path):
    """
    加载已保存的url详情CSV，返回loc到详情的映射。
    """
    if not os.path.exists(file_path):
        return {}
    url_map = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url_map[row['loc']] = row
    return url_map

def save_url_details_csv(url_details, file_path):
    """
    保存url详情到CSV文件。
    """
    with open(file_path, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['loc', 'lastmodified', 'added_date']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for d in url_details:
            writer.writerow(d)

def main():
    setup_logging()
    entry_url = input("请输入 sitemap 入口 URL: ").strip()
    today = datetime.now().strftime('%Y-%m-%d')
    details_file = f"url_details.csv"
    existing_url_map = load_url_details_csv(details_file)
    existing_url_date_map = {k: v['added_date'] for k, v in existing_url_map.items()}
    all_url_details = list(existing_url_map.values())
    url_details = collect_all_url_details_from_sitemap(entry_url, existing_url_date_map=existing_url_date_map, today=today)
    # 合并去重
    loc_set = set(existing_url_map.keys())
    for detail in url_details:
        if detail['loc'] not in loc_set:
            all_url_details.append(detail)
            loc_set.add(detail['loc'])
    save_url_details_csv(all_url_details, details_file)
    print(f"共采集到 {len(all_url_details)} 条URL详情，已保存到 {details_file}")

if __name__ == "__main__":
    main()
