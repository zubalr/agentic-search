import json
import requests
import time

START_INDEX = 0
END_INDEX = 1000

API_URL = "http://172.16.201.69:8086/solr/getGisDataUsingFuzzySearch"
INPUT_FILE = "analytics.json"
OUTPUT_FILE = f"api_results_{START_INDEX}_{END_INDEX-1}.jsonl"
FAILED_FILE = f"failed_{START_INDEX}_{END_INDEX-1}.jsonl"

MAX_RETRIES = 3
TIMEOUT = 30  # seconds
BACKOFF_FACTOR = 2

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
    return None, "Unknown error"

def main():
    with open(INPUT_FILE, "r") as f:
        data = json.load(f)["SEARCH KEYWORDS"]

    batch = data[START_INDEX:END_INDEX]
    for i, item in enumerate(batch, start=START_INDEX):
        payload = json.loads(item["payload"])
        params = {
            "searchKeyWord": payload["searchKeyword"],
            "originLat": payload["originLat"],
            "originLng": payload["originLng"],
            "inputLanguage": 1
        }
        result, error = fetch_with_retries(params)
        if result is not None:
            with open(OUTPUT_FILE, "a") as out:
                out.write(json.dumps(result) + "\n")
        else:
            with open(FAILED_FILE, "a") as fail:
                fail.write(json.dumps({"params": params, "error": error}) + "\n")
        if (i - START_INDEX + 1) % 50 == 0:
            print(f"Processed {i - START_INDEX + 1} / {END_INDEX - START_INDEX} items")

if __name__ == "__main__":
    main()