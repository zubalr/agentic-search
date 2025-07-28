"""
Data IO utilities: load/save results, memory, etc.

Handles reading and writing JSONL files for results and memory.
"""

import json
import os
import logging
from typing import Dict

def load_results(file_path: str) -> Dict[str, Dict]:
    """
    Loads a JSONL result file into a dictionary mapping query to result.
    Returns an empty dict if file is missing or malformed.
    """
    results = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if query := data.get("query"):
                        results[query] = data.get("result", {})
                except (json.JSONDecodeError, KeyError) as e:
                    logging.warning(f"Skipping malformed line in {file_path}: {line.strip()} - Error: {e}")
    except FileNotFoundError:
        logging.error(f"Input file not found: {file_path}")
    except Exception as e:
        logging.error(f"Error loading results from {file_path}: {e}")
    return results

def load_memory(file_path: str) -> Dict[str, Dict]:
    """
    Loads existing comparisons from the memory file to avoid re-processing.
    Returns an empty dict if file is missing or malformed.
    """
    memory = {}
    if not os.path.exists(file_path):
        return memory
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if query := data.get("query"):
                        memory[query] = data.get("comparison")
                except (json.JSONDecodeError, KeyError):
                    continue
    except Exception as e:
        logging.error(f"Error loading memory from {file_path}: {e}")
    return memory

def save_comparison(file_path: str, query: str, comparison: Dict):
    """
    Saves a new comparison to the memory file.
    Appends a JSONL record for the given query and comparison.
    """
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            record = {"query": query, "comparison": comparison}
            f.write(json.dumps(record) + "\n")
    except IOError as e:
        logging.error(f"Could not write to memory file {file_path}: {e}")
