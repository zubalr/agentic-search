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

from src.core.api_client import load_queries_from_csv, APIQuery, GooglePlacesAPIClient

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



# Only keep these keys for comparison
IMPORTANT_PLACE_KEYS = [
    "id", "displayName", "formattedAddress", "location", "types", "websiteUri",
    "internationalPhoneNumber", "rating", "userRatingCount", "businessStatus", "currentOpeningHours"
]

def filter_place_dict(place):
    """
    Return a new dict with only the important keys for comparison.
    Handles nested keys for displayName, location, currentOpeningHours.
    """
    if not isinstance(place, dict):
        return place
    filtered = {}
    for k in IMPORTANT_PLACE_KEYS:
        if k in place:
            if k == "displayName" and isinstance(place[k], dict):
                filtered[k] = {"text": place[k].get("text")}
            elif k == "location" and isinstance(place[k], dict):
                filtered[k] = {
                    "latitude": place[k].get("latitude"),
                    "longitude": place[k].get("longitude")
                }
            elif k == "currentOpeningHours" and isinstance(place[k], dict):
                filtered[k] = {"open_now": place[k].get("open_now")}
            else:
                filtered[k] = place[k]
    return filtered

def filter_places(places):
    if not isinstance(places, list):
        return places
    return [filter_place_dict(place) for place in places]

def filter_result_places(result):
    if not isinstance(result, dict):
        return result
    if "places" in result:
        result["places"] = filter_places(result["places"])
    return result

def fetch_all_places_info(client: GooglePlacesAPIClient, query: APIQuery, field_mask: str):
    """
    For a given query, perform text search, nearby search, and fetch details for all unique places.
    Returns a dict with only important tags for comparison.
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
    text_result = filter_result_places(text_resp.result)
    results["text_search"] = text_result
    if not text_resp.success and text_resp.error:
        results["errors"].append(f"text_search: {text_resp.error}")
    # Nearby Search
    nearby_resp = client.search_nearby(query, field_mask)
    nearby_result = filter_result_places(nearby_resp.result)
    results["nearby_search"] = nearby_result
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
        # Filter details to keep only important tags
        filtered_details = filter_place_dict(details) if isinstance(details, dict) else details
        if filtered_details:
            results["place_details"].append(filtered_details)
        if err:
            results["errors"].append(f"place_details {pid}: {err}")
    return results

def fetch_all_places_info(client: GooglePlacesAPIClient, query: APIQuery, field_mask: str):
    """
    For a given query, perform text search, nearby search, and fetch details for all unique places.
    Returns a dict with all results and errors, with 'photos' and 'reviews' removed from all places.
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
    text_result = filter_result_places(text_resp.result)
    results["text_search"] = text_result
    if not text_resp.success and text_resp.error:
        results["errors"].append(f"text_search: {text_resp.error}")
    # Nearby Search
    nearby_resp = client.search_nearby(query, field_mask)
    nearby_result = filter_result_places(nearby_resp.result)
    results["nearby_search"] = nearby_result
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
        # Remove photos and reviews from place details
        if isinstance(details, dict):
            details.pop('photos', None)
            details.pop('reviews', None)
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
            all_info = fetch_all_places_info(client, query, "*")  # Always use "*" to get all fields
            out.write(json.dumps(all_info) + "\n")

    print(f"Done. Results saved to {args.output}")

if __name__ == "__main__":
    main()
