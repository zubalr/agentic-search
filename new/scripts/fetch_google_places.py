#!/usr/bin/env python3
"""
Fetch a range of keywords from the CSV using the new Google Maps Places API (v1).
Usage:
    python scripts/fetch_google_places.py --start 0 --end 10 --field-mask "places.displayName,places.formattedAddress,places.types,places.websiteUri,places.formattedPhoneNumber,places.rating,places.userRatingCount"
"""
import os
import sys
import argparse
import json
from pathlib import Path

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
from src.core.api_client import load_queries_from_csv, APIQuery, GooglePlacesAPIClient
import requests


# Debug sys.path
print("sys.path:", sys.path)

# Load .env if present
def load_env_file(env_path: str = ".env"):
    if not os.path.exists(env_path):
        return
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                value = value.strip('"').strip("'")
                os.environ[key] = value
load_env_file()

# Try importing src.core.api_client, fallback to core.api_client if needed
try:
    from src.core.api_client import load_queries_from_csv, APIQuery, GooglePlacesAPIClient
except ModuleNotFoundError:
    from core.api_client import load_queries_from_csv, APIQuery, GooglePlacesAPIClient

def fetch_all_places_info(client: GooglePlacesAPIClient, query: APIQuery, field_mask: str):
    """
    For a given query, perform text search, nearby search, and fetch details for all unique places.
    Returns a dict with all results and errors.
    """
    results = {
        "query": {"keyword": query.keyword, "lat": query.lat, "lng": query.lng},
        "text_search": None,
        "nearby_search": None,
        "place_details": [],
        "errors": []
    }
    # Text Search
    text_resp = client.search_text(query, field_mask)
    results["text_search"] = text_resp.result
    if not text_resp.success and text_resp.error:
        results["errors"].append(f"text_search: {text_resp.error}")
    # Nearby Search
    nearby_resp = client.search_nearby(query, field_mask)
    results["nearby_search"] = nearby_resp.result
    if not nearby_resp.success and nearby_resp.error:
        results["errors"].append(f"nearby_search: {nearby_resp.error}")
    # Collect unique place IDs from both searches
    place_ids = set()
    for resp in [text_resp, nearby_resp]:
        if resp and resp.result and "places" in resp.result:
            for place in resp.result["places"]:
                if "id" in place:
                    place_ids.add(place["id"])
    # Fetch details for each unique place ID
    for pid in place_ids:
        details, err = client.get_place_details(pid, field_mask)
        if details:
            results["place_details"].append(details)
        if err:
            results["errors"].append(f"place_details {pid}: {err}")
    return results

def main():
    parser = argparse.ArgumentParser(description="Fetch a range of keywords from the CSV using Google Maps Places API (v1)")
    parser.add_argument('--start', type=int, required=True, help='Start index (inclusive)')
    parser.add_argument('--end', type=int, required=True, help='End index (exclusive)')
    parser.add_argument('--csv', default='data/representative_keywords_with_location.csv', help='CSV file with keywords')
    parser.add_argument('--field-mask', default='places.displayName,places.formattedAddress,places.types,places.websiteUri,places.formattedPhoneNumber,places.rating,places.userRatingCount', help='Comma-separated list of fields to return')
    parser.add_argument('--output', default='raw/google_places_custom.jsonl', help='Output JSONL file')
    args = parser.parse_args()

    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        print("GOOGLE_PLACES_API_KEY not set in environment or .env file.")
        sys.exit(1)

    queries = load_queries_from_csv(args.csv)
    queries = queries[args.start:args.end]
    print(f"Fetching {len(queries)} queries from index {args.start} to {args.end}...")

    client = GooglePlacesAPIClient(api_key=api_key)

    with open(args.output, 'w') as out:
        for i, query in enumerate(queries):
            print(f"[{i+1}/{len(queries)}] {query.keyword}")
            all_info = fetch_all_places_info(client, query, args.field_mask)
            out.write(json.dumps(all_info) + "\n")

    print(f"Done. Results saved to {args.output}")

if __name__ == "__main__":
    main()
