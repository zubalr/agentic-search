import json
import requests
import time
import logging
import os

# --- Configuration ---
START_INDEX = 0
END_INDEX = 500

API_URL = "http://172.16.201.69:8086/solr/getGisDataUsingFuzzySearch"
INPUT_FILE = os.path.join(os.path.dirname(__file__), '../data/Analytics.json')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), f'../raw/api_results_{START_INDEX}_{END_INDEX-1}.jsonl')
FAILED_FILE = os.path.join(os.path.dirname(__file__), f'../raw/failed_{START_INDEX}_{END_INDEX-1}.jsonl')

MAX_RETRIES = 3
TIMEOUT = 30  # seconds
BACKOFF_FACTOR = 2
# --- End Configuration ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_with_retries(params):
    """Fetches data from the internal Solr API with retries and exponential backoff."""
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
    try:
        with open(INPUT_FILE, "r") as f:
            data = json.load(f)["SEARCH KEYWORDS"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        logging.error(f"Could not read or parse input file '{INPUT_FILE}': {e}")
        return

    batch = data[START_INDEX:END_INDEX]
    total_items = len(batch)

    # Open files once to be more efficient
    with open(OUTPUT_FILE, "a") as out_file, open(FAILED_FILE, "a") as fail_file:
        logging.info(f"Starting to process {total_items} search queries...")
        for i, item in enumerate(batch, start=1):
            try:
                payload = json.loads(item["payload"])
                query = payload["searchKeyword"]
                params = {
                    "searchKeyWord": query,
                    "originLat": payload["originLat"],
                    "originLng": payload["originLng"],
                    "inputLanguage": 1
                }
            except (json.JSONDecodeError, KeyError) as e:
                logging.error(f"Skipping item {i} due to invalid payload: {item} - {e}")
                continue

            result, error = fetch_with_retries(params)

            if result is not None:
                # Store the query along with the result for easy comparison later
                out_file.write(json.dumps({"query": query, "result": result}) + "\n")
            else:
                fail_file.write(json.dumps({"query": query, "error": error}) + "\n")

            if i % 50 == 0 or i == total_items:
                logging.info(f"Processed {i} / {total_items} items")

    logging.info(f"Processing complete. Results in '{OUTPUT_FILE}', failures in '{FAILED_FILE}'.")

if __name__ == "__main__":
    main()