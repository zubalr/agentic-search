#!/usr/bin/env python3
"""
Data fetching script for Google Places Autocomplete (New) API and Solr API.
Mirrors the CLI and structure of fetch_data_with_latlng.py for consistency.

Usage:
    python3 scripts/fetch_autocomplete_with_latlng.py --source solr --keywords-file data/representative_keywords_with_location.csv
    python3 scripts/fetch_autocomplete_with_latlng.py --source google --keywords "restaurant,cafe,hotel"
    python3 scripts/fetch_autocomplete_with_latlng.py --source both --range 0 100
    python3 scripts/fetch_autocomplete_with_latlng.py --source both --keywords-file data/representative_keywords_with_location.csv --lat 25.276987 --lng 55.296249
"""

import argparse
import asyncio
import sys
from pathlib import Path
import os
import json
import requests

# Ensure project root is in sys.path for src imports
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.api_client import SolrAPIClient, load_queries_from_csv, APIQuery
from src.utils.config import get_config
from src.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)

# --- Filtering functions for Solr ---
IMPORTANT_SOLR_KEYS = [
    "itemId", "entryId", "name", "poiName", "containerName", "location", "poiCategoryId",
    "poiSubCategoryId", "callTypeEnum", "contact", "popularity", "score"
]
def filter_solr_result(result):
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

# --- Google Autocomplete (New) API logic ---
AUTOCOMPLETE_URL = "https://places.googleapis.com/v1/places:autocomplete"

def fetch_google_autocomplete(api_key, query, field_mask="*", **kwargs):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": field_mask
    }
    body = {
        "input": query.keyword
    }
    # Add locationBias or locationRestriction if lat/lng present
    if query.lat and query.lng:
        # Use locationBias as a circle of 5000m radius by default
        body["locationBias"] = {
            "circle": {
                "center": {"latitude": query.lat, "longitude": query.lng},
                "radius": 5000.0
            }
        }
    # Add any extra kwargs (for future extensibility)
    body.update(kwargs)
    resp = requests.post(AUTOCOMPLETE_URL, headers=headers, json=body, timeout=10)
    try:
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Google Autocomplete API error for '{query.keyword}': {e} | Response: {resp.text}")
        return {"error": str(e), "response": resp.text}

async def main():
    parser = argparse.ArgumentParser(description='Fetch data from Google Autocomplete (New) API and Solr API (with optional lat/lng override)')
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
    parser.add_argument('--lat', type=float, help='Override latitude for all queries')
    parser.add_argument('--lng', type=float, help='Override longitude for all queries')
    args = parser.parse_args()

    setup_logging(args.log_level)
    config = get_config()
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip('"').strip("'")
                    os.environ[key] = value

    queries = []
    default_keywords_file_path = Path(__file__).parent.parent / "data/uniquerepresentative_keywords_with_location.csv"

    if args.keywords_file:
        if not Path(args.keywords_file).exists():
            logger.error(f"Keywords file not found: {args.keywords_file}")
            return
        logger.info(f"Loading keywords from specified file: {args.keywords_file}")
        queries = load_queries_from_csv(args.keywords_file)
    elif args.keywords:
        keywords = [kw.strip() for kw in args.keywords.split(',')]
        logger.info("Loading keywords from command-line argument.")
        queries = [APIQuery(keyword=kw, lat=config.default_lat, lng=config.default_lng) for kw in keywords]
    else:
        if default_keywords_file_path.exists():
            logger.info(f"No specific keywords source provided. Using default keywords file: {default_keywords_file_path}")
            queries = load_queries_from_csv(str(default_keywords_file_path))
        else:
            logger.error(f"Default keywords file not found at {default_keywords_file_path}. Use --keywords-file or --keywords argument.")
            return

    # Override lat/lng if provided, or set to default if not present
    default_lat = 25.3246603
    default_lng = 51.4382779
    if args.lat is not None and args.lng is not None:
        for q in queries:
            q.lat = args.lat
            q.lng = args.lng
        logger.info(f"Overriding all queries to use lat={args.lat}, lng={args.lng}")
    else:
        for q in queries:
            if not q.lat or not q.lng:
                q.lat = default_lat
                q.lng = default_lng
        logger.info(f"Setting default lat/lng for queries without location: lat={default_lat}, lng={default_lng}")

    if args.range:
        start, end = args.range
        queries = queries[start:end]
        logger.info(f"Processing queries {start} to {end}")

    logger.info(f"Processing {len(queries)} queries")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.source in ['solr', 'both']:
        logger.info("Fetching from Solr API...")
        solr_client = SolrAPIClient()
        solr_responses = solr_client.batch_search(queries)
        filtered_solr_responses = [filter_solr_result(r) for r in solr_responses]
        if args.range:
            start, end = args.range
            solr_success_file = output_dir / f"api_results_solr_{start}_{end}.jsonl"
        else:
            solr_success_file = output_dir / "api_results_solr.jsonl"
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

    if args.source in ['google', 'both']:
        api_key = os.getenv("GOOGLE_PLACES_API_KEY") or getattr(config, 'google_places_api_key', None)
        if not api_key:
            logger.error("Google Places API key not found. Set GOOGLE_PLACES_API_KEY environment variable.")
            return
        logger.info("Fetching from Google Places Autocomplete (New) API...")
        google_responses = []
        for i, query in enumerate(queries):
            try:
                logger.info(f"[Google Autocomplete] Fetching for query {i+1}/{len(queries)}: {query.keyword} (lat={query.lat}, lng={query.lng})")
                # Explicitly request fields to ensure structuredFormat is included, using correct field mask paths
                field_mask = "suggestions.placePrediction.text,suggestions.placePrediction.structuredFormat"
                result = fetch_google_autocomplete(api_key, query, field_mask=field_mask, includeQueryPredictions=True)
                google_responses.append({"query": query.keyword, "response": result})
                logger.info(f"[Google Autocomplete] Success for query {i+1}/{len(queries)}: {query.keyword}")
            except Exception as e:
                logger.error(f"Error fetching Google Autocomplete for query {query.keyword}: {e}")
        if args.range:
            start, end = args.range
            google_success_file = output_dir / f"google_autocomplete_results_{start}_{end}.jsonl"
        else:
            google_success_file = output_dir / "google_autocomplete_results.jsonl"
        with open(google_success_file, 'w', encoding='utf-8') as f:
            for resp in google_responses:
                f.write(json.dumps(resp) + '\n')
        logger.info(f"Google Autocomplete results saved to {google_success_file}")

    logger.info("Data fetching completed successfully!")

if __name__ == '__main__':
    asyncio.run(main())
