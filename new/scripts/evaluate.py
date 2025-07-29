#!/usr/bin/env python3
"""
Evaluation script for comparing search results using LLM judges and other evaluation methods.

Usage:
    python scripts/evaluate.py --mode batch --evaluator llm_judge
    python scripts/evaluate.py --mode sequential --evaluator deepeval --model cerebras/llama3-70b-instruct
"""

import argparse
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.evaluation.comparison import create_comparison_engine
from src.evaluation.deepeval_runner import create_deepeval_evaluator
from src.data.io import DataIO
from src.core.evaluator import EvaluationMode
from src.utils.config import get_config
from src.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)

async def run_llm_judge_evaluation(args):
    """Run LLM Judge evaluation."""
    config = get_config()
    
    # Load result files
    internal_file = args.internal_results or config.internal_results_file
    google_file = args.google_results or config.google_results_file
    
    if not Path(internal_file).exists():
        logger.error(f"Internal results file not found: {internal_file}")
        logger.info("Run data fetching first: python scripts/fetch_data.py --source both")
        return
    
    if not Path(google_file).exists():
        logger.error(f"Google results file not found: {google_file}")
        logger.info("Run data fetching first: python scripts/fetch_data.py --source both")
        return
    
    logger.info("Loading search results...")
    internal_results = DataIO.load_search_results(internal_file)
    google_results = DataIO.load_search_results(google_file)
    
    logger.info(f"Loaded {len(internal_results)} internal results and {len(google_results)} Google results")
    
    # Load existing comparisons to avoid reprocessing
    comparison_memory = DataIO.load_comparison_memory(args.output_file)
    logger.info(f"Found {len(comparison_memory)} existing comparisons")
    
    # Set up evaluation configuration
    eval_config = None
    if args.model:
        eval_config = {'llm_models': [{"provider": "custom", "model_name": args.model}]}
    
    engine = create_comparison_engine(eval_config)
    mode = EvaluationMode.BATCH if args.mode == 'batch' else EvaluationMode.SEQUENTIAL
    
    if args.mode == 'batch':
        kwargs = {
            'batch_size': args.batch_size,
            'delay_between_batches': args.delay if args.mode == 'batch' else 0,
            'skip_processed': True,
            'comparison_memory': comparison_memory
        }
    else:
        kwargs = {
            'batch_size': args.batch_size,
            'delay_between_batches': args.delay if args.mode == 'batch' else 0,
            'delay_between_queries': args.delay if args.mode == 'sequential' else 2.0,
            'skip_processed': True,
            'comparison_memory': comparison_memory
        }
    
    logger.info(f"Starting LLM Judge evaluation in {args.mode} mode...")
    results = await engine.compare_results(internal_results, google_results, mode, **kwargs)
    
    # Save results
    if results['results']:
        DataIO.save_comparisons_batch(args.output_file, results['results'])
        logger.info(f"Saved {len(results['results'])} new comparisons to {args.output_file}")
        
        # Generate summary
        summary_file = args.output_file.replace('.jsonl', '_summary.json')
        summary = DataIO.export_results_summary(results['results'], summary_file)
        logger.info(f"Summary saved to {summary_file}")
        
        # Print summary
        logger.info("\\nEvaluation Summary:")
        logger.info(f"  Total new comparisons: {summary['total_comparisons']}")
        logger.info(f"  Average internal score: {summary['average_internal_score']:.2f}")
        logger.info(f"  Average Google score: {summary['average_google_score']:.2f}")
        logger.info("  Verdict distribution:")
        for verdict, count in summary['verdict_distribution'].items():
            logger.info(f"    {verdict}: {count}")
    else:
        logger.info("No new comparisons generated (all queries already processed)")

async def run_deepeval_evaluation(args):
    """Run DeepEval evaluation."""
    logger.info("Starting DeepEval evaluation...")
    
    try:
        evaluator = create_deepeval_evaluator(args.model or "cerebras/llama3-70b-instruct")
        
        # For DeepEval, we need existing comparison results
        if not Path(args.output_file).exists():
            logger.error(f"Comparison results file not found: {args.output_file}")
            logger.info("Run LLM judge evaluation first: python scripts/evaluate.py --evaluator llm_judge")
            return
        
        results = evaluator.evaluate_from_files(
            results_file=args.output_file,
            references_file=args.references_file
        )
        
        # Save DeepEval results
        deepeval_output = args.output_file.replace('.jsonl', '_deepeval.json')
        with open(deepeval_output, 'w') as f:
            import json
            json.dump(results, f, indent=2)
        
        logger.info(f"DeepEval results saved to {deepeval_output}")
        
        # Print results
        logger.info("\\nDeepEval Results:")
        for metric_name, metric_data in results.get('metric_scores', {}).items():
            score = metric_data.get('score', 'N/A')
            logger.info(f"  {metric_name}: {score}")
            
    except ImportError:
        logger.error("DeepEval not available. Please install: pip install deepeval")
    except Exception as e:
        logger.error(f"Error running DeepEval: {e}")

async def main():
    parser = argparse.ArgumentParser(description='Evaluate and compare search results')
    parser.add_argument('--mode', choices=['batch', 'sequential'], default='batch',
                       help='Processing mode')
    parser.add_argument('--evaluator', choices=['llm_judge', 'deepeval'], default='llm_judge',
                       help='Evaluation method')
    parser.add_argument('--internal-results', 
                       help='Path to internal API results file')
    parser.add_argument('--google-results',
                       help='Path to Google Places results file')
    parser.add_argument('--output-file', default='output/comparison_memory.jsonl',
                       help='Output file for comparison results')
    parser.add_argument('--references-file',
                       help='Path to human reference labels (for DeepEval)')
    parser.add_argument('--batch-size', type=int, default=5,
                       help='Batch size for concurrent processing')
    parser.add_argument('--delay', type=float, default=10.0,
                       help='Delay between batches/queries (seconds)')
    parser.add_argument('--model', 
                       help='Override default LLM model')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    
    # Ensure output directory exists
    Path(args.output_file).parent.mkdir(parents=True, exist_ok=True)
    
    try:
        if args.evaluator == 'llm_judge':
            await run_llm_judge_evaluation(args)
        elif args.evaluator == 'deepeval':
            await run_deepeval_evaluation(args)
        
        logger.info("Evaluation completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Evaluation cancelled by user")
    except Exception as e:
        logger.error(f"Error during evaluation: {e}")
        if args.log_level == 'DEBUG':
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
