import csv
import json
import requests
import time
import os
import logging
import argparse
from dotenv import load_dotenv

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
API_URL = "https://places.googleapis.com/v1/places:searchText"
INPUT_FILE = os.path.join(os.path.dirname(__file__), '../data/representative_keywords_with_location.csv')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '../raw/google_places_results_with_location.jsonl')
FAILED_FILE = os.path.join(os.path.dirname(__file__), '../raw/google_places_failed_with_location.jsonl')
MAX_RETRIES = 3
TIMEOUT = 30  # seconds
BACKOFF_FACTOR = 2
FIELD_MASK = "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount"

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")


def parse_args():
    parser = argparse.ArgumentParser(description="Fetch Google Places API data using keywords and location.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--all', action='store_true', help='Process all queries in the CSV')
    group.add_argument('--range', nargs=2, type=int, metavar=('START', 'END'), help='Process a range of rows (by index)')
    group.add_argument('--list', type=str, help='Comma-separated list of keywords to process')
    return parser.parse_args()


def read_csv():
    queries = []
    invalid_rows = []
    with open(INPUT_FILE, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if len(row) < 3:
                continue
            col1, col2, col3 = row[0].strip(), row[1].strip(), row[2].strip()
            # Skip header or rows with None/lat/lng
            if col1.lower() in ('keyword', 'lat', 'lng', '', 'none') or col2.lower() in ('lat', 'lng', '', 'none') or col3.lower() in ('lat', 'lng', '', 'none'):
                continue
            # Detect if first column is a coordinate (lat or lng)
            def is_float(val):
                try:
                    float(val)
                    return True
                except ValueError:
                    return False
            # If col1 looks like a coordinate, treat col1 as lat, col2 as lng, col3 as keyword
            if is_float(col1) and is_float(col2):
                keyword, lat, lng = col3, col1, col2
            else:
                keyword, lat, lng = col1, col2, col3
            # Validate lat/lng
            if not keyword or not is_float(lat) or not is_float(lng):
                invalid_rows.append({'keyword': keyword, 'lat': lat, 'lng': lng, 'error': 'Invalid lat/lng'})
                continue
            queries.append({'keyword': keyword, 'lat': lat, 'lng': lng})
    return queries, invalid_rows


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


def fetch_places_with_retries(session, query, lat, lng):
    delay = 2
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    # Use locationBias with circle for lat/lng
    data = {
        "textQuery": query,
        "locationBias": {
            "circle": {
                "center": {"latitude": float(lat), "longitude": float(lng)},
                "radius": 1000.0  # meters, can be adjusted
            }
        }
    }
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.post(API_URL, json=data, headers=headers, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json(), None
        except requests.exceptions.RequestException as e:
            logging.warning(f"Attempt {attempt}/{MAX_RETRIES} failed for query '{query}': {e}")
            if attempt == MAX_RETRIES:
                return None, str(e)
            time.sleep(delay)
            delay *= BACKOFF_FACTOR
    return None, "All retry attempts failed"


def main():
    # Ensure raw/ directory exists
    raw_dir = os.path.join(os.path.dirname(__file__), '../raw')
    os.makedirs(raw_dir, exist_ok=True)
    if not API_KEY:
        logging.error("API key not found. Set GOOGLE_PLACES_API_KEY in your .env file.")
        return
    args = parse_args()
    queries, invalid_rows = read_csv()
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
        start_idx, end_idx = 0, len(read_csv()[0])
    elif args.list:
        start_idx, end_idx = 0, len(selected)
    else:
        start_idx, end_idx = 0, total_items
    results_file = os.path.join(raw_dir, f"google_places_results_{start_idx}_{end_idx}.jsonl")
    failed_file = os.path.join(raw_dir, f"google_places_failed_{start_idx}_{end_idx}.jsonl")
    with requests.Session() as session, open(results_file, "w") as out_file, open(failed_file, "w") as fail_file:
        logging.info(f"Starting to process {total_items} queries...")
        # Log invalid rows as failures
        for inv in invalid_rows:
            fail_file.write(json.dumps({"query": inv, "error": inv['error']}) + "\n")
        for i, item in enumerate(selected, start=1):
            try:
                lat_f = float(item['lat'])
                lng_f = float(item['lng'])
            except ValueError:
                fail_file.write(json.dumps({"query": item, "error": "Invalid lat/lng"}) + "\n")
                continue
            result, error = fetch_places_with_retries(session, item['keyword'], item['lat'], item['lng'])
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
