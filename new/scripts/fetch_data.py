#!/usr/bin/env python3
"""
Data fetching script for APIs.
Simplified interface for fetching data from Solr and Google Places APIs.

Usage:
    python scripts/fetch_data.py --source solr --keywords-file data/representative_keywords_with_location.csv
    python scripts/fetch_data.py --source google --keywords "restaurant,cafe,hotel"
    python scripts/fetch_data.py --source both --range 0 100
"""


import argparse
import asyncio
import sys
from pathlib import Path
import os
import json

# Ensure project root is in sys.path for src imports
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.api_client import SolrAPIClient, GooglePlacesAPIClient, load_queries_from_csv, APIQuery

# --- Filtering functions for comparison ---
IMPORTANT_GOOGLE_KEYS = [
    "id", "displayName", "formattedAddress", "location", "types", "websiteUri",
    "internationalPhoneNumber", "rating", "userRatingCount", "businessStatus", "currentOpeningHours"
]
def filter_google_place(place):
    if not isinstance(place, dict):
        return place
    filtered = {}
    for k in IMPORTANT_GOOGLE_KEYS:
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

def filter_google_response(resp):
    # Handles dicts with 'places' key, or lists of places
    if isinstance(resp, dict) and "places" in resp:
        resp["places"] = [filter_google_place(p) for p in resp["places"]]
    elif isinstance(resp, list):
        resp = [filter_google_place(p) for p in resp]
    return resp

def filter_google_result(result):
    # Handles top-level result dicts from batch_search
    if not isinstance(result, dict):
        return result
    filtered = {"query": result.get("query", {})}
    for key in ["text_search", "nearby_search", "place_details"]:
        val = result.get(key)
        if isinstance(val, dict) and "places" in val:
            filtered[key] = filter_google_response(val)
        elif isinstance(val, list):
            filtered[key] = [filter_google_place(p) for p in val]
        else:
            filtered[key] = val
    filtered["errors"] = result.get("errors", [])
    return filtered

# --- Solr filtering ---
IMPORTANT_SOLR_KEYS = [
    "itemId", "entryId", "name", "poiName", "containerName", "location", "poiCategoryId",
    "poiSubCategoryId", "callTypeEnum", "contact", "popularity", "score"
]
def filter_solr_result(result):
    # Handles top-level result dicts from batch_search
    if not isinstance(result, dict):
        return result
    filtered = {"query": result.get("query", {})}
    solr = result.get("result", {})
    filtered_result = {}
    for k in IMPORTANT_SOLR_KEYS:
        if k in solr:
            if k == "location" and isinstance(solr[k], dict):
                filtered_result[k] = {
                    "lat": solr[k].get("lat"),
                    "lng": solr[k].get("lng")
                }
            else:
                filtered_result[k] = solr[k]
    filtered["result"] = filtered_result
    return filtered
from src.utils.config import get_config
from src.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)

async def main():
    parser = argparse.ArgumentParser(description='Fetch data from APIs')
    parser.add_argument('--source', choices=['solr', 'google', 'both'], required=True,
                       help='API source to fetch from')
    parser.add_argument('--keywords-file', 
                       help='CSV file with keywords and locations')
    parser.add_argument('--keywords', 
                       help='Comma-separated list of keywords')
    parser.add_argument('--output-dir', default='raw',
                       help='Output directory for results')
    parser.add_argument('--range', nargs=2, type=int, metavar=('START', 'END'),
                       help='Process a range of queries by index')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    
    config = get_config()
    # Load .env if present
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip('"').strip("'")
                    os.environ[key] = value
    
    # Prepare queries
    queries = []
    
    if args.keywords_file:
        if not Path(args.keywords_file).exists():
            logger.error(f"Keywords file not found: {args.keywords_file}")
            return
        queries = load_queries_from_csv(args.keywords_file)
    elif args.keywords:
        # Create queries from keyword list
        keywords = [kw.strip() for kw in args.keywords.split(',')]
        queries = [APIQuery(keyword=kw, lat=config.default_lat, lng=config.default_lng) for kw in keywords]
    else:
        # Use default keywords file
        default_file = config.keywords_csv
        if Path(default_file).exists():
            queries = load_queries_from_csv(default_file)
        else:
            logger.error("No keywords file found. Use --keywords-file or --keywords argument.")
            return
    
    # Filter queries if range specified
    if args.range:
        start, end = args.range
        queries = queries[start:end]
        logger.info(f"Processing queries {start} to {end}")
    
    logger.info(f"Processing {len(queries)} queries")
    
    # Ensure output directory exists
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Fetch from Solr API
    if args.source in ['solr', 'both']:
        logger.info("Fetching from Solr API...")
        solr_client = SolrAPIClient()
        solr_responses = solr_client.batch_search(queries)
        # Filter responses
        filtered_solr_responses = [filter_solr_result(r) for r in solr_responses]
        # Determine output filename
        if args.range:
            start, end = args.range
            solr_success_file = output_dir / f"api_results_solr_{start}_{end}.jsonl"
            solr_failed_file = output_dir / f"api_failed_solr_{start}_{end}.jsonl"
        else:
            solr_success_file = output_dir / "api_results_solr.jsonl"
            solr_failed_file = output_dir / "api_failed_solr.jsonl"
        # Save filtered Solr responses
        def make_json_serializable(obj):
            if isinstance(obj, dict):
                return {k: make_json_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_json_serializable(v) for v in obj]
            elif hasattr(obj, 'to_dict'):
                return obj.to_dict()
            elif hasattr(obj, '__dict__'):
                return {k: make_json_serializable(v) for k, v in obj.__dict__.items()}
            else:
                return obj
        for resp in filtered_solr_responses:
            serializable = make_json_serializable(resp)
            with open(solr_success_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(serializable) + '\n')
        logger.info(f"Solr results saved to {solr_success_file}")
    
    # Fetch from Google Places API
    if args.source in ['google', 'both']:
        api_key = os.getenv("GOOGLE_PLACES_API_KEY") or getattr(config, 'google_places_api_key', None)
        if not api_key:
            logger.error("Google Places API key not found. Set GOOGLE_PLACES_API_KEY environment variable.")
            return
        logger.info("Fetching from Google Places API...")
        google_client = GooglePlacesAPIClient(api_key)
        google_responses = []
        for i, query in enumerate(queries):
            try:
                # Use your existing per-query fetch function (e.g., fetch_all_places_info)
                from scripts.fetch_google_places import fetch_all_places_info
                result = fetch_all_places_info(google_client, query, "*")
                filtered = filter_google_result(result)
                google_responses.append(filtered)
            except Exception as e:
                logger.error(f"Error fetching Google Places for query {query.keyword}: {e}")
        # Determine output filename
        if args.range:
            start, end = args.range
            google_success_file = output_dir / f"google_places_results_{start}_{end}.jsonl"
            google_failed_file = output_dir / f"google_places_failed_{start}_{end}.jsonl"
        else:
            google_success_file = output_dir / "google_places_results.jsonl"
            google_failed_file = output_dir / "google_places_failed.jsonl"
        # Save filtered responses
        # Use a simple JSONL save for dicts
        with open(google_success_file, 'w', encoding='utf-8') as f:
            for resp in google_responses:
                f.write(json.dumps(resp) + '\n')
        logger.info(f"Google Places results saved to {google_success_file}")
    
    logger.info("Data fetching completed successfully!")

if __name__ == '__main__':
    asyncio.run(main())
