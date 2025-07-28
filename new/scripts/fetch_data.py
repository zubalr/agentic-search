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

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.api_client import SolrAPIClient, GooglePlacesAPIClient, load_queries_from_csv, save_responses_to_jsonl, APIQuery
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
        
        # Determine output filename
        if args.range:
            start, end = args.range
            solr_success_file = output_dir / f"api_results_solr_{start}_{end}.jsonl"
            solr_failed_file = output_dir / f"api_failed_solr_{start}_{end}.jsonl"
        else:
            solr_success_file = output_dir / "api_results_solr.jsonl"
            solr_failed_file = output_dir / "api_failed_solr.jsonl"
        
        save_responses_to_jsonl(solr_responses, str(solr_success_file), str(solr_failed_file))
        logger.info(f"Solr results saved to {solr_success_file}")
    
    # Fetch from Google Places API
    if args.source in ['google', 'both']:
        if not config.google_places_api_key:
            logger.error("Google Places API key not found. Set GOOGLE_PLACES_API_KEY environment variable.")
            return
        
        logger.info("Fetching from Google Places API...")
        google_client = GooglePlacesAPIClient(config.google_places_api_key)
        google_responses = google_client.batch_search(queries)
        
        # Determine output filename
        if args.range:
            start, end = args.range
            google_success_file = output_dir / f"google_places_results_{start}_{end}.jsonl"
            google_failed_file = output_dir / f"google_places_failed_{start}_{end}.jsonl"
        else:
            google_success_file = output_dir / "google_places_results.jsonl"
            google_failed_file = output_dir / "google_places_failed.jsonl"
        
        save_responses_to_jsonl(google_responses, str(google_success_file), str(google_failed_file))
        logger.info(f"Google Places results saved to {google_success_file}")
    
    logger.info("Data fetching completed successfully!")

if __name__ == '__main__':
    asyncio.run(main())
