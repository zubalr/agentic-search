#!/usr/bin/env python3
"""
Data processing script for keyword extraction and preparation.
Handles the complete pipeline from analytics data to processed keywords.

Usage:
    python scripts/process_data.py --analytics-file data/Analytics.json
    python scripts/process_data.py --max-keywords 1000 --output-dir processed_data
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.data_processor import DataProcessor
from src.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Process and extract keywords from analytics data')
    parser.add_argument('--analytics-file', default='data/Analytics.json',
                       help='Input analytics JSON file')
    parser.add_argument('--output-dir', default='data',
                       help='Output directory for processed files')
    parser.add_argument('--max-keywords', type=int, default=500,
                       help='Maximum number of representative keywords')
    parser.add_argument('--add-location', action='store_true', default=True,
                       help='Add default location to keywords')
    parser.add_argument('--lat', default='24.8607',
                       help='Default latitude (Karachi)')
    parser.add_argument('--lng', default='67.0011',
                       help='Default longitude (Karachi)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    
    logger.info("Starting keyword processing pipeline...")
    
    # Check if analytics file exists
    if not Path(args.analytics_file).exists():
        logger.error(f"Analytics file not found: {args.analytics_file}")
        logger.info("Please ensure the Analytics.json file exists in the data/ directory")
        return
    
    try:
        # Run the processing pipeline
        output_files = DataProcessor.process_pipeline(
            analytics_file=args.analytics_file,
            output_dir=args.output_dir,
            max_keywords=args.max_keywords,
            add_location=args.add_location,
            default_lat=args.lat,
            default_lng=args.lng
        )
        
        logger.info("Processing pipeline completed successfully!")
        logger.info("Generated files:")
        for file_type, file_path in output_files.items():
            logger.info(f"  {file_type}: {file_path}")
        
        # Summary information
        if 'representative_with_location' in output_files:
            csv_file = output_files['representative_with_location']
            keywords_with_location = DataProcessor.load_keywords_from_csv(csv_file)
            logger.info(f"\\nReady for API fetching:")
            logger.info(f"  Keywords with location: {len(keywords_with_location)}")
            logger.info(f"  Use: python scripts/fetch_data.py --keywords-file {csv_file}")
        
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        if args.log_level == 'DEBUG':
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
