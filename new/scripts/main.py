#!/usr/bin/env python3
"""
Main CLI entry point for the Agentic Search LLM Judge System.

This script provides a unified interface for all operations:
- Data fetching from APIs
- Data processing and keyword extraction
- Result evaluation and comparison
- Analysis and reporting

Usage:
    python scripts/main.py --help
    python scripts/main.py fetch --help
    python scripts/main.py process --help
    python scripts/main.py evaluate --help
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.utils.config import get_config
from src.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)

def setup_fetch_parser(subparsers):
    """Set up the fetch command parser."""
    fetch_parser = subparsers.add_parser('fetch', help='Fetch data from APIs')
    fetch_parser.add_argument('--source', choices=['solr', 'google', 'both'], default='both',
                            help='API source to fetch from')
    fetch_parser.add_argument('--keywords-file', 
                            help='CSV file with keywords and locations')
    fetch_parser.add_argument('--output-dir', default='raw',
                            help='Output directory for results')
    fetch_parser.add_argument('--batch-size', type=int, default=50,
                            help='Batch size for processing')
    fetch_parser.add_argument('--range', nargs=2, type=int, metavar=('START', 'END'),
                            help='Process a range of queries by index')
    fetch_parser.add_argument('--keywords', 
                            help='Comma-separated list of specific keywords to process')

def setup_process_parser(subparsers):
    """Set up the process command parser."""
    process_parser = subparsers.add_parser('process', help='Process and extract keywords')
    process_parser.add_argument('--analytics-file', default='data/Analytics.json',
                               help='Input analytics JSON file')
    process_parser.add_argument('--output-dir', default='data',
                               help='Output directory for processed files')
    process_parser.add_argument('--max-keywords', type=int, default=500,
                               help='Maximum number of representative keywords')
    process_parser.add_argument('--add-location', action='store_true', default=True,
                               help='Add default location to keywords')
    process_parser.add_argument('--lat', default='24.8607',
                               help='Default latitude (Karachi)')
    process_parser.add_argument('--lng', default='67.0011',
                               help='Default longitude (Karachi)')

def setup_evaluate_parser(subparsers):
    """Set up the evaluate command parser."""
    eval_parser = subparsers.add_parser('evaluate', help='Evaluate and compare results')
    eval_parser.add_argument('--mode', choices=['batch', 'sequential'], default='batch',
                           help='Processing mode')
    eval_parser.add_argument('--evaluator', choices=['llm_judge', 'deepeval'], default='llm_judge',
                           help='Evaluation method')
    eval_parser.add_argument('--internal-results', 
                           help='Path to internal API results file')
    eval_parser.add_argument('--google-results',
                           help='Path to Google Places results file')
    eval_parser.add_argument('--output-file', default='output/comparison_memory.jsonl',
                           help='Output file for comparison results')
    eval_parser.add_argument('--batch-size', type=int, default=5,
                           help='Batch size for concurrent processing')
    eval_parser.add_argument('--delay', type=float, default=10.0,
                           help='Delay between batches (seconds)')
    eval_parser.add_argument('--model', 
                           help='Override default LLM model')

async def fetch_command(args):
    """Execute the fetch command."""
    from src.core.api_client import SolrAPIClient, GooglePlacesAPIClient, load_queries_from_csv, save_responses_to_jsonl
    from src.utils.config import get_config
    
    config = get_config()
    
    # Load queries
    keywords_file = args.keywords_file or config.keywords_csv
    if not Path(keywords_file).exists():
        logger.error(f"Keywords file not found: {keywords_file}")
        return
    
    queries = load_queries_from_csv(keywords_file)
    logger.info(f"Loaded {len(queries)} queries from {keywords_file}")
    
    # Filter queries if specified
    if args.range:
        start, end = args.range
        queries = queries[start:end]
        logger.info(f"Processing queries {start} to {end}")
    elif args.keywords:
        wanted_keywords = set(kw.strip() for kw in args.keywords.split(','))
        queries = [q for q in queries if q.keyword in wanted_keywords]
        logger.info(f"Processing {len(queries)} specified keywords")
    
    # Ensure output directory exists
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Fetch from Solr API
    if args.source in ['solr', 'both']:
        logger.info("Fetching from Solr API...")
        solr_client = SolrAPIClient()
        solr_responses = solr_client.batch_search(queries)
        
        solr_success_file = output_dir / "api_results_solr.jsonl"
        solr_failed_file = output_dir / "api_failed_solr.jsonl"
        save_responses_to_jsonl(solr_responses, str(solr_success_file), str(solr_failed_file))
    
    # Fetch from Google Places API
    if args.source in ['google', 'both']:
        if not config.google_places_api_key:
            logger.error("Google Places API key not found in environment")
            return
        
        logger.info("Fetching from Google Places API...")
        google_client = GooglePlacesAPIClient(config.google_places_api_key)
        google_responses = google_client.batch_search(queries)
        
        google_success_file = output_dir / "google_places_results.jsonl"
        google_failed_file = output_dir / "google_places_failed.jsonl"
        save_responses_to_jsonl(google_responses, str(google_success_file), str(google_failed_file))

def process_command(args):
    """Execute the process command."""
    from src.core.data_processor import DataProcessor
    
    logger.info("Starting keyword processing pipeline...")
    
    if not Path(args.analytics_file).exists():
        logger.error(f"Analytics file not found: {args.analytics_file}")
        return
    
    output_files = DataProcessor.process_pipeline(
        analytics_file=args.analytics_file,
        output_dir=args.output_dir,
        max_keywords=args.max_keywords,
        add_location=args.add_location,
        default_lat=args.lat,
        default_lng=args.lng
    )
    
    logger.info("Processing complete! Generated files:")
    for file_type, file_path in output_files.items():
        logger.info(f"  {file_type}: {file_path}")

async def evaluate_command(args):
    """Execute the evaluate command."""
    from src.evaluation.comparison import create_comparison_engine
    from src.evaluation.deepeval_runner import create_deepeval_evaluator
    from src.data.io import DataIO
    from src.core.evaluator import EvaluationMode
    
    config = get_config()
    
    # Load result files
    internal_file = args.internal_results or config.internal_results_file
    google_file = args.google_results or config.google_results_file
    
    if not Path(internal_file).exists():
        logger.error(f"Internal results file not found: {internal_file}")
        return
    
    if not Path(google_file).exists():
        logger.error(f"Google results file not found: {google_file}")
        return
    
    logger.info("Loading search results...")
    internal_results = DataIO.load_search_results(internal_file)
    google_results = DataIO.load_search_results(google_file)
    
    # Load existing comparisons to avoid reprocessing
    comparison_memory = DataIO.load_comparison_memory(args.output_file)
    
    mode = EvaluationMode.BATCH if args.mode == 'batch' else EvaluationMode.SEQUENTIAL
    
    if args.evaluator == 'llm_judge':
        # LLM Judge evaluation
        logger.info("Starting LLM Judge evaluation...")
        
        # Override model if specified
        eval_config = None
        if args.model:
            eval_config = {'llm_models': [{"provider": "custom", "model_name": args.model}]}
        
        engine = create_comparison_engine(eval_config)
        
        kwargs = {
            'batch_size': args.batch_size,
            'delay_between_batches': args.delay,
            'skip_processed': True,
            'comparison_memory': comparison_memory
        }
        
        results = await engine.compare_results(internal_results, google_results, mode, **kwargs)
        
        # Save results
        if results['results']:
            DataIO.save_comparisons_batch(args.output_file, results['results'])
            logger.info(f"Saved {len(results['results'])} new comparisons to {args.output_file}")
    
    elif args.evaluator == 'deepeval':
        # DeepEval evaluation
        logger.info("Starting DeepEval evaluation...")
        
        try:
            evaluator = create_deepeval_evaluator(args.model or config.deepeval_model)
            
            # For DeepEval, we need existing comparison results
            if not comparison_memory:
                logger.error("DeepEval requires existing comparison results. Run LLM judge evaluation first.")
                return
            
            comparison_results = list(comparison_memory.values())
            results = evaluator.evaluate(
                internal_results, 
                google_results, 
                mode,
                comparison_results=comparison_results
            )
            
            # Save DeepEval results
            deepeval_output = args.output_file.replace('.jsonl', '_deepeval.json')
            with open(deepeval_output, 'w') as f:
                import json
                json.dump(results, f, indent=2)
            
            logger.info(f"DeepEval results saved to {deepeval_output}")
            
        except ImportError:
            logger.error("DeepEval not available. Please install: pip install deepeval")

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Agentic Search LLM Judge System',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                      default='INFO', help='Logging level')
    parser.add_argument('--log-file', help='Log file path')
    parser.add_argument('--config-file', help='Configuration file path')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Set up subcommand parsers
    setup_fetch_parser(subparsers)
    setup_process_parser(subparsers)
    setup_evaluate_parser(subparsers)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Set up logging
    setup_logging(args.log_level, args.log_file)
    
    # Load configuration
    if args.config_file:
        from src.utils.config import load_config_from_file
        load_config_from_file(args.config_file)
    
    logger.info(f"Starting {args.command} command...")
    
    try:
        # Execute the appropriate command
        if args.command == 'fetch':
            asyncio.run(fetch_command(args))
        elif args.command == 'process':
            process_command(args)
        elif args.command == 'evaluate':
            asyncio.run(evaluate_command(args))
        
        logger.info(f"{args.command} command completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
    except Exception as e:
        logger.error(f"Error executing {args.command} command: {e}")
        if args.log_level == 'DEBUG':
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
