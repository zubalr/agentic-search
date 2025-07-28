#!/usr/bin/env python3
"""
Simple runner script for the agentic search system.
Reads configuration from config.json and executes the full pipeline.

Usage:
    python run.py
    python run.py --config custom_config.json
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

def load_env_file(env_path: str = ".env"):
    """Load environment variables from .env file."""
    if not os.path.exists(env_path):
        return
    
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"').strip("'")
                    os.environ[key] = value
    except Exception as e:
        print(f"Warning: Could not load .env file: {e}")

# Load environment variables from .env file
load_env_file()

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.api_client import SolrAPIClient, GooglePlacesAPIClient, load_queries_from_csv, save_responses_to_jsonl
from src.utils.config import get_config
from src.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)

def load_simple_config(config_path: str = "config.json") -> Dict[str, Any]:
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        # Validate required configuration keys
        validate_config(config)
        return config
        
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing config file: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

def validate_config(config: Dict[str, Any]) -> None:
    """Validate that all required configuration keys are present."""
    required_keys = {
        "keywords": ["file"],
        "apis": ["fetch_from"],
        "processing": ["mode"],
        "output": ["raw_dir"]
    }
    
    # Check if use_range is true, then start_index and end_index are required
    if config.get("keywords", {}).get("use_range", False):
        required_keys["keywords"].extend(["start_index", "end_index"])
    
    # Check if sequential mode, then delays are required
    if config.get("processing", {}).get("mode") == "sequential":
        required_keys["processing"].append("delay_between_requests")
        if config.get("apis", {}).get("fetch_from") == "both":
            required_keys["processing"].append("delay_between_apis")
    
    # Check if evaluation is enabled, then provider and model are required
    if config.get("evaluation", {}).get("run_evaluation", False):
        required_keys["evaluation"] = ["llm_provider", "model"]
    
    for section, keys in required_keys.items():
        if section not in config:
            raise ValueError(f"Missing required section: {section}")
        
        for key in keys:
            if key not in config[section]:
                raise ValueError(f"Missing required key '{key}' in section '{section}'")

async def fetch_data(config: Dict[str, Any]) -> None:
    """Fetch data from APIs based on configuration."""
    keywords_config = config["keywords"]
    api_config = config["apis"]
    output_config = config["output"]
    processing_config = config["processing"]
    
    # Load queries from CSV
    keywords_file = keywords_config["file"]
    if not Path(keywords_file).exists():
        logger.error(f"Keywords file not found: {keywords_file}")
        return
    
    logger.info(f"Loading keywords from {keywords_file}")
    all_queries = load_queries_from_csv(keywords_file)
    
    # Apply range if specified
    if keywords_config.get("use_range", False):
        start_idx = keywords_config["start_index"]
        end_idx = keywords_config["end_index"]
        queries = all_queries[start_idx:end_idx]
        logger.info(f"Processing queries {start_idx} to {end_idx} ({len(queries)} total)")
        range_suffix = f"_{start_idx}_{end_idx}" if output_config.get("include_range_in_filename", False) else ""
    else:
        queries = all_queries
        logger.info(f"Processing all {len(queries)} queries")
        range_suffix = ""
    
    # Ensure output directory exists
    output_dir = Path(output_config["raw_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    
    fetch_from = api_config["fetch_from"].lower()
    processing_mode = processing_config.get("mode", "sequential")
    
    logger.info(f"Processing mode: {processing_mode}")
    
    # Fetch from Solr API
    if fetch_from in ["solr", "both"]:
        logger.info("Fetching from Solr API...")
        solr_client = SolrAPIClient()
        
        try:
            if processing_mode == "sequential":
                solr_responses = await fetch_sequential(
                    solr_client, queries, processing_config, "Solr"
                )
            else:  # batch mode
                solr_responses = solr_client.batch_search(queries)
            
            solr_success_file = output_dir / f"api_results_solr{range_suffix}.jsonl"
            solr_failed_file = output_dir / f"api_failed_solr{range_suffix}.jsonl"
            
            save_responses_to_jsonl(solr_responses, str(solr_success_file), str(solr_failed_file))
            logger.info(f"Solr results saved to {solr_success_file}")
            
        except Exception as e:
            logger.error(f"Error fetching from Solr API: {e}")
    
    # Add delay between APIs if processing both
    if fetch_from == "both" and processing_mode == "sequential":
        api_delay = processing_config["delay_between_apis"]
        logger.info(f"Waiting {api_delay}s between APIs...")
        await asyncio.sleep(api_delay)
    
    # Fetch from Google Places API
    if fetch_from in ["google", "both"]:
        logger.info("Fetching from Google Places API...")
        
        # Get API key from environment
        google_api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if not google_api_key:
            logger.error("GOOGLE_PLACES_API_KEY environment variable not set")
            return
        
        google_client = GooglePlacesAPIClient(api_key=google_api_key)
        
        try:
            if processing_mode == "sequential":
                google_responses = await fetch_sequential(
                    google_client, queries, processing_config, "Google Places"
                )
            else:  # batch mode
                google_responses = google_client.batch_search(queries)
            
            google_success_file = output_dir / f"google_places_results{range_suffix}.jsonl"
            google_failed_file = output_dir / f"google_places_failed{range_suffix}.jsonl"
            
            save_responses_to_jsonl(google_responses, str(google_success_file), str(google_failed_file))
            logger.info(f"Google Places results saved to {google_success_file}")
            
        except Exception as e:
            logger.error(f"Error fetching from Google Places API: {e}")

async def fetch_sequential(client, queries, processing_config, api_name):
    """Fetch data sequentially with delays between requests."""
    delay = processing_config["delay_between_requests"]
    responses = []
    
    logger.info(f"Processing {len(queries)} queries sequentially for {api_name} (delay: {delay}s)")
    
    for i, query in enumerate(queries):
        try:
            logger.info(f"Processing query {i+1}/{len(queries)}: {query.keyword}")
            response = client.search(query)  # Pass the APIQuery object directly
            responses.append(response)
            
            # Add delay between requests (except for the last one)
            if i < len(queries) - 1:
                await asyncio.sleep(delay)
                
        except Exception as e:
            logger.error(f"Error processing query {i+1} ({query.keyword}): {e}")
            # Continue with next query even if one fails
            continue
    
    return responses

async def run_evaluation(config: Dict[str, Any]) -> None:
    """Run evaluation if enabled in configuration."""
    eval_config = config.get("evaluation", {})
    
    if not eval_config.get("run_evaluation", False):
        logger.info("Evaluation disabled in configuration")
        return
    
    logger.info("Running evaluation...")
    
    try:
        # Import evaluation modules
        from src.evaluation.llm_judge import LLMJudge
        from src.evaluation.comparison import ComparisonRunner
        
        # Set up LLM judge
        llm_judge = LLMJudge(
            provider=eval_config["llm_provider"],
            model=eval_config["model"]
        )
        
        # Run comparison
        comparison_runner = ComparisonRunner(llm_judge)
        
        # Determine input files based on range
        keywords_config = config["keywords"]
        output_config = config["output"]
        
        if keywords_config.get("use_range", False) and output_config.get("include_range_in_filename", False):
            start_idx = keywords_config["start_index"]
            end_idx = keywords_config["end_index"]
            range_suffix = f"_{start_idx}_{end_idx}"
        else:
            range_suffix = ""
        
        raw_dir = Path(output_config["raw_dir"])
        output_dir = Path(output_config["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        solr_file = raw_dir / f"api_results_solr{range_suffix}.jsonl"
        google_file = raw_dir / f"google_places_results{range_suffix}.jsonl"
        comparison_file = output_dir / f"comparison_results{range_suffix}.jsonl"
        
        if solr_file.exists() and google_file.exists():
            await comparison_runner.compare_results(
                str(solr_file),
                str(google_file),
                str(comparison_file)
            )
            logger.info(f"Evaluation results saved to {comparison_file}")
        else:
            logger.warning(f"Input files not found for evaluation: {solr_file}, {google_file}")
            
    except Exception as e:
        logger.error(f"Error during evaluation: {e}")

def print_config_summary(config: Dict[str, Any]) -> None:
    """Print a summary of the current configuration."""
    logger.info("=== Configuration Summary ===")
    
    keywords_config = config["keywords"]
    processing_config = config["processing"]
    
    logger.info(f"Keywords file: {keywords_config['file']}")
    
    if keywords_config.get("use_range", False):
        start = keywords_config["start_index"]
        end = keywords_config["end_index"]
        logger.info(f"Processing range: {start} to {end}")
    else:
        logger.info("Processing all keywords")
    
    logger.info(f"Fetching from: {config['apis']['fetch_from']}")
    
    processing_mode = processing_config.get("mode", "sequential")
    logger.info(f"Processing mode: {processing_mode}")
    
    if processing_mode == "sequential":
        delay = processing_config["delay_between_requests"]
        logger.info(f"Delay between requests: {delay}s")
        if config['apis']['fetch_from'] == "both":
            api_delay = processing_config["delay_between_apis"]
            logger.info(f"Delay between APIs: {api_delay}s")
    else:
        batch_config = config.get("_batch_processing_options", {})
        batch_size = batch_config.get("_batch_size", 50)
        logger.info(f"Batch size: {batch_size}")
    
    logger.info(f"Output directory: {config['output']['raw_dir']}")
    
    if config.get("evaluation", {}).get("run_evaluation", False):
        eval_config = config["evaluation"]
        logger.info(f"Evaluation enabled: {eval_config['llm_provider']}/{eval_config['model']}")
    else:
        logger.info("Evaluation disabled")
    
    logger.info("=" * 30)

async def main():
    parser = argparse.ArgumentParser(description='Run the agentic search system')
    parser.add_argument('--config', default='config.json',
                       help='Path to configuration file (default: config.json)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show configuration and exit without running')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_simple_config(args.config)
    
    # Set up logging
    logging_config = config.get("logging", {})
    log_level = logging_config.get("level", "INFO")
    setup_logging(log_level)
    
    # Print configuration summary
    print_config_summary(config)
    
    if args.dry_run:
        logger.info("Dry run mode - exiting without processing")
        return
    
    try:
        # Fetch data
        await fetch_data(config)
        
        # Run evaluation if enabled
        await run_evaluation(config)
        
        logger.info("All operations completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
