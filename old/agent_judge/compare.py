"""
Main orchestration logic for comparing results.

Provides async functions for batch and sequential processing of queries using LLM judge.
"""

import asyncio
import logging
from .llm_judge import LLMManager, judge_query
from .data_io import load_results, load_memory, save_comparison
from .config import (
    INTERNAL_RESULTS_FILE, GOOGLE_RESULTS_FILE, COMPARISON_MEMORY_FILE, FAILED_QUERIES_FILE,
    BATCH_SIZE, DELAY_BETWEEN_BATCHES_S, DEFAULT_LLM_MODELS
)

async def process_queries_batch(llm_models=None, batch_size=None, delay_s=None):
    """
    Process all queries in batches.
    Each batch is processed concurrently, with a delay between batches.
    """
    llm_models = llm_models or DEFAULT_LLM_MODELS
    batch_size = batch_size or BATCH_SIZE
    delay_s = delay_s or DELAY_BETWEEN_BATCHES_S
    internal_results = load_results(INTERNAL_RESULTS_FILE)
    google_results = load_results(GOOGLE_RESULTS_FILE)
    comparison_memory = load_memory(COMPARISON_MEMORY_FILE)
    llm_manager = LLMManager(llm_models)
    queries_to_process = [q for q in internal_results if q not in comparison_memory]
    for i in range(0, len(queries_to_process), batch_size):
        batch = queries_to_process[i:i + batch_size]
        tasks = []
        for query in batch:
            if query in google_results:
                tasks.append(_process_and_save(query, internal_results[query], google_results[query], llm_manager))
            else:
                logging.warning(f"Query '{query}' not in Google results. Skipping.")
        await asyncio.gather(*tasks)
        if (i + batch_size) < len(queries_to_process):
            logging.info(f"--- Batch {i//batch_size + 1} finished. Waiting for {delay_s} seconds... ---")
            await asyncio.sleep(delay_s)

async def process_queries_sequential(llm_models=None, delay_s=None):
    """
    Process all queries one by one, with optional delay between each.
    Each query is processed in order, with a delay after each.
    """
    llm_models = llm_models or DEFAULT_LLM_MODELS
    delay_s = delay_s or DELAY_BETWEEN_BATCHES_S
    internal_results = load_results(INTERNAL_RESULTS_FILE)
    google_results = load_results(GOOGLE_RESULTS_FILE)
    comparison_memory = load_memory(COMPARISON_MEMORY_FILE)
    llm_manager = LLMManager(llm_models)
    queries_to_process = [q for q in internal_results if q not in comparison_memory]
    for idx, query in enumerate(queries_to_process):
        if query in google_results:
            await _process_and_save(query, internal_results[query], google_results[query], llm_manager)
        else:
            logging.warning(f"Query '{query}' not in Google results. Skipping.")
        if (idx + 1) < len(queries_to_process):
            logging.info(f"--- Query {idx+1} finished. Waiting for {delay_s} seconds... ---")
            await asyncio.sleep(delay_s)

async def _process_and_save(query, internal_res, google_res, llm_manager):
    """
    Helper to process a single query and save the result or log failure.
    """
    from .config import COMPARISON_MEMORY_FILE, FAILED_QUERIES_FILE
    result = await judge_query(query, internal_res, google_res, llm_manager)
    if result:
        save_comparison(COMPARISON_MEMORY_FILE, query, result)
    else:
        with open(FAILED_QUERIES_FILE, "a", encoding="utf-8") as f:
            f.write(f"{query}\n")
