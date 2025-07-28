"""
Configuration and constants for agent_judge system.

Holds file paths, default LLM model configs, and batch/sequential settings.
All values can be overridden by environment variables or CLI args.
"""

import os

# File paths (can be overridden by CLI or env)
INTERNAL_RESULTS_FILE = os.getenv("INTERNAL_RESULTS_FILE", "api_results_0_499.jsonl")
GOOGLE_RESULTS_FILE = os.getenv("GOOGLE_RESULTS_FILE", "google_places_results_0_499.jsonl")
COMPARISON_MEMORY_FILE = os.getenv("COMPARISON_MEMORY_FILE", "comparison_memory.jsonl")
FAILED_QUERIES_FILE = os.getenv("FAILED_QUERIES_FILE", "failed_queries.txt")

# Default LLM model configs (can be overridden by CLI)
DEFAULT_LLM_MODELS = [
    {"provider": "cerebras", "model_name": "llama-3.3-70b"},
]

# Default batch/sequential settings
BATCH_SIZE = 5
DELAY_BETWEEN_BATCHES_S = 10
