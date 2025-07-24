import json
import requests
import time
import os
from dotenv import load_dotenv
import logging

# --- Configuration ---
# Set up basic logging to provide clear feedback during execution
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

START_INDEX = 0
END_INDEX = 500

# This is the correct endpoint for the Places API (New) Text Search
GOOGLE_PLACES_API_URL = "https://places.googleapis.com/v1/places:searchText"
INPUT_FILE = os.path.join(os.path.dirname(__file__), '../data/Analytics.json')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), f'../raw/google_places_results_{START_INDEX}_{END_INDEX-1}.jsonl')
FAILED_FILE = os.path.join(os.path.dirname(__file__), f'../raw/google_places_failed_{START_INDEX}_{END_INDEX-1}.jsonl')

MAX_RETRIES = 3
TIMEOUT = 30  # seconds
BACKOFF_FACTOR = 2

# Load environment variables from .env file
load_dotenv()
# Get API key from environment variables. The script will fail safely if not found.
API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

# **IMPORTANT**: Define the fields you want from the API.
# This is REQUIRED by the new API and directly controls your cost.
# See https://developers.google.com/maps/documentation/places/web-service/place-data-fields
# for a full list of fields and their associated billing SKUs.
# Using '*' will request all fields and result in the highest cost.
FIELD_MASK = "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount"


def fetch_places_with_retries(session, query):
    """
    Fetches data from Google Places API (New) using a POST request with retries
    and exponential backoff.

    Args:
        session: A requests.Session object for connection pooling.
        query: The search string to send to the API.

    Returns:
        A tuple of (result_json, error_string). One will be None.
    """
    delay = 2
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    data = {"textQuery": query}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # The new API uses a POST request with a JSON body
            response = session.post(
                GOOGLE_PLACES_API_URL, json=data, headers=headers, timeout=TIMEOUT
            )
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
    if not API_KEY:
        logging.error("API key not found. Set GOOGLE_PLACES_API_KEY in your .env file.")
        return

    try:
        with open(INPUT_FILE, "r") as f:
            data = json.load(f)["SEARCH KEYWORDS"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        logging.error(f"Could not read or parse input file '{INPUT_FILE}': {e}")
        return

    batch = data[START_INDEX:END_INDEX]
    total_items = len(batch)

    # Use a session for connection pooling and open files once to be efficient
    with requests.Session() as session, open(OUTPUT_FILE, "a") as out_file, open(
        FAILED_FILE, "a"
    ) as fail_file:
        logging.info(f"Starting to process {total_items} search queries...")
        for i, item in enumerate(batch, start=1):
            try:
                payload = json.loads(item["payload"])
                query = payload["searchKeyword"]
            except (json.JSONDecodeError, KeyError) as e:
                logging.error(f"Skipping item {i} due to invalid payload: {item} - {e}")
                continue

            result, error = fetch_places_with_retries(session, query)

            if result is not None:
                # Include the original query for better traceability
                out_file.write(json.dumps({"query": query, "result": result}) + "\n")
            else:
                fail_file.write(json.dumps({"query": query, "error": error}) + "\n")

            if i % 50 == 0 or i == total_items:
                logging.info(f"Processed {i} / {total_items} items")

    logging.info(f"Processing complete. Results in '{OUTPUT_FILE}', failures in '{FAILED_FILE}'.")


if __name__ == "__main__":
    main()
