"""
Entry point for running the comparison system. Supports batch and sequential modes.

Usage:
    python scripts/main.py --mode batch
    python scripts/main.py --mode sequential
"""

import argparse
import asyncio
import logging
import sys
sys.path.append("..")  # Ensure agent_judge is importable
from agent_judge.compare import process_queries_batch, process_queries_sequential

def main():
    """
    Parse CLI arguments and run the comparison system in the selected mode.
    """
    parser = argparse.ArgumentParser(description="LLM-based Search Result Comparison System")
    parser.add_argument('--mode', choices=['batch', 'sequential'], default='batch', help='Processing mode')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    if args.mode == 'batch':
        asyncio.run(process_queries_batch())
    else:
        asyncio.run(process_queries_sequential())

if __name__ == "__main__":
    main()
