import csv
import json
import requests
import time
import logging
import argparse
import os

# --- Configuration ---
API_URL = "http://172.16.201.69:8086/solr/getGisDataUsingFuzzySearch"
INPUT_FILE = os.path.join(os.path.dirname(__file__), '../data/representative_keywords_with_location.csv')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '../raw/api_results_solr.jsonl')
FAILED_FILE = os.path.join(os.path.dirname(__file__), '../raw/failed_solr.jsonl')
MAX_RETRIES = 3
TIMEOUT = 30  # seconds
BACKOFF_FACTOR = 2
# --- End Configuration ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_args():
    parser = argparse.ArgumentParser(description="Fetch Solr API data using keywords and location.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--all', action='store_true', help='Process all queries in the CSV')
    group.add_argument('--range', nargs=2, type=int, metavar=('START', 'END'), help='Process a range of rows (by index)')
    group.add_argument('--list', type=str, help='Comma-separated list of keywords to process')
    return parser.parse_args()

def read_csv():
    queries = []
    with open(INPUT_FILE, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if len(row) < 3:
                continue
            keyword, lat, lng = row[0].strip(), row[1].strip(), row[2].strip()
            if not keyword or not lat or not lng:
                continue
            queries.append({'keyword': keyword, 'lat': lat, 'lng': lng})
    return queries

def select_queries(queries, args):
    if args.all:
        return queries
    elif args.range:
        start, end = args.range
        return queries[start:end]
    elif args.list:
        wanted = set([q.strip() for q in args.list.split(',')])
        selected = [q for q in queries if q['keyword'] in wanted]
        not_found = wanted - set(q['keyword'] for q in selected)
        return selected, not_found
    return [], set()

def fetch_with_retries(params):
    delay = 2
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(API_URL, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json(), None
        except Exception as e:
            if attempt == MAX_RETRIES:
                return None, str(e)
            time.sleep(delay)
            delay *= BACKOFF_FACTOR
    return None, "All retry attempts failed"

def main():
    # Ensure raw/ directory exists
    raw_dir = os.path.join(os.path.dirname(__file__), '../raw')
    os.makedirs(raw_dir, exist_ok=True)
    args = parse_args()
    queries = read_csv()
    if args.list:
        selected, not_found = select_queries(queries, args)
    else:
        selected = select_queries(queries, args)
        not_found = set()
    total_items = len(selected)
    # Determine range for output file naming
    if args.range:
        start_idx, end_idx = args.range
    elif args.all:
        start_idx, end_idx = 0, len(read_csv())
    elif args.list:
        start_idx, end_idx = 0, len(selected)
    else:
        start_idx, end_idx = 0, total_items
    results_file = os.path.join(raw_dir, f"api_results_solr_{start_idx}_{end_idx}.jsonl")
    failed_file = os.path.join(raw_dir, f"api_failed_solr_{start_idx}_{end_idx}.jsonl")
    logging.info(f"Starting to process {total_items} queries...")
    with open(results_file, "w") as out_file, open(failed_file, "w") as fail_file:
        for i, item in enumerate(selected, start=1):
            params = {
                "searchKeyWord": item['keyword'],
                "originLat": item['lat'],
                "originLng": item['lng'],
                "inputLanguage": 1
            }
            result, error = fetch_with_retries(params)
            if result is not None:
                out_file.write(json.dumps({"query": item, "result": result}) + "\n")
            else:
                fail_file.write(json.dumps({"query": item, "error": error}) + "\n")
            if i % 50 == 0 or i == total_items:
                logging.info(f"Processed {i} / {total_items} items")
        if not_found:
            for keyword in not_found:
                fail_file.write(json.dumps({"query": keyword, "error": "Keyword not found in CSV"}) + "\n")
    logging.info(f"Processing complete. Results in '{results_file}', failures in '{failed_file}'.")

if __name__ == "__main__":
    main()
