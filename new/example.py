#!/usr/bin/env python3
"""
Example usage of the refactored agentic search system.
This demonstrates the key features and workflow.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.logger import setup_logging, get_logger
from src.utils.config import get_config

def main():
    # Set up logging
    setup_logging("INFO")
    logger = get_logger(__name__)
    
    logger.info("🚀 Agentic Search LLM Judge System - Refactored")
    logger.info("=" * 60)
    
    # Show configuration
    config = get_config()
    logger.info("📋 Configuration:")
    logger.info(f"  Data directory: {config.data_dir}")
    logger.info(f"  Batch size: {config.batch_size}")
    logger.info(f"  Default location: {config.default_lat}, {config.default_lng}")
    logger.info(f"  LLM models: {len(config.llm_models)} configured")
    
    # Show available scripts
    logger.info("\n🛠️  Available Scripts:")
    scripts_dir = Path(__file__).parent / "scripts"
    for script in scripts_dir.glob("*.py"):
        logger.info(f"  python scripts/{script.name}")
    
    # Show workflow
    logger.info("\n📝 Recommended Workflow:")
    logger.info("1. Process data:     python scripts/process_data.py")
    logger.info("2. Fetch APIs:       python scripts/fetch_data.py --source both")
    logger.info("3. Evaluate:         python scripts/evaluate.py --evaluator llm_judge")
    
    # Show main CLI
    logger.info("\n🎯 Or use the main CLI:")
    logger.info("  python scripts/main.py --help")
    
    logger.info("\n✅ System is ready to use!")
    
if __name__ == "__main__":
    main()
