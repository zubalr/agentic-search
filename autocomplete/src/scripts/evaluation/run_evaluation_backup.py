# src/scripts/evaluation/run_evaluation.py

import os
import json
import logging
import time
from tqdm import tqdm
from typing import List, Dict, Any

# Import both the pair-wise and holistic evaluation functions
from src.core.evaluation import evaluate_single_pair, evaluate_holistic_set

# Optional: project logger if present; otherwise configure basic logging here.
try:
    from src.utils.logger import get_logger  # project-provided logger
    logger = get_logger(__name__)
except Exception:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logger = logging.getLogger("evaluation.run_evaluation")

def calculate_advanced_metrics(solr_list: List[Dict], google_list: List[Dict]) -> Dict[str, Any]:
    """
    Calculates Coverage, Precision, and MRR metrics using the pair-wise evaluator as a building block.
    """
    if not solr_list or not google_list:
        return {
            "coverage_per_google_poi": {},
            "precision_ratio": 0,
            "mean_reciprocal_rank": 0
        }
        
    # --- Coverage & MRR Calculation ---
    coverage_report = {}
    reciprocal_ranks = []
    
    for google_poi in google_list:
        best_match_for_google_poi = {"score": -1, "rank": -1}
        for i, solr_poi in enumerate(solr_list):
            eval_result = evaluate_single_pair(solr_poi, google_poi)
            if eval_result["score"] > best_match_for_google_poi["score"]:
                best_match_for_google_poi = {"score": eval_result["score"], "rank": i + 1}
        
        google_poi_name = google_poi.get('main_text', 'Unknown Google POI')
        coverage_report[google_poi_name] = best_match_for_google_poi
        
        # If a relevant match was found (score > 5), add its reciprocal rank
        if best_match_for_google_poi["score"] > 5:
            reciprocal_ranks.append(1 / best_match_for_google_poi["rank"])

    # --- Precision Calculation ---
    relevant_solr_results = 0
    relevance_threshold = 5.0  # We consider a Solr result "relevant" if it scores > 5 against ANY Google result
    
    for solr_poi in solr_list:
        is_relevant = False
        for google_poi in google_list:
            if evaluate_single_pair(solr_poi, google_poi)["score"] >= relevance_threshold:
                is_relevant = True
                break
        if is_relevant:
            relevant_solr_results += 1
            
    precision_ratio = relevant_solr_results / len(solr_list) if solr_list else 0
    mean_reciprocal_rank = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0

    return {
        "coverage_per_google_poi": coverage_report,
        "precision_ratio": precision_ratio,
        "mean_reciprocal_rank": mean_reciprocal_rank
    }

def main():
    """Main function to load data, orchestrate the holistic evaluation, and save a detailed report."""
    input_path = os.getenv("EVAL_INPUT_PATH", "data/results/merged_filtered_results.jsonl")
    output_path = os.getenv("EVAL_OUTPUT_JSONL", "data/results/advanced_evaluation_report.jsonl")

    # Verbose flag from env to control detailed logs
    verbose = os.getenv("EVAL_VERBOSE", "0") in {"1", "true", "True"}
    if verbose:
        logger.setLevel(logging.DEBUG)

    logger.info(f"Loading data from: {input_path}")
    if not os.path.exists(input_path):
        logger.error(f"Input file not found at '{input_path}'")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    logger.info(f"Found {len(records)} records. Output will be written incrementally to: {output_path}")
    if verbose:
        logger.debug("Verbose logging enabled (EVAL_VERBOSE=1).")

    logger.info(f"Starting advanced evaluation for {len(records)} queries...")
    final_report = []

    for record in tqdm(records, desc="Evaluating Queries"):
        query = record.get("query", "Unknown Query")
        solr_list = record.get("solr_results", [])
        google_list = record.get("google_autocomplete_results", [])

        # Per-query header
        logger.info(f"[Query] {query}")
        logger.info(f"  - Solr results: {len(solr_list)} | Google results: {len(google_list)}")

        # Format lists into a consistent dictionary structure
        solr_formatted = [{"poi_name": r.get("solr_poiName"), "container": r.get("solr_containerName")} for r in solr_list]
        google_formatted = [{"main_text": r.get("google_main_text"), "secondary_text": r.get("google_secondary_text")} for r in google_list]

        if verbose:
            preview_solr = solr_formatted[:3]
            preview_google = google_formatted[:3]
            logger.debug("  - Sample Solr: %s", json.dumps(preview_solr, ensure_ascii=False))
            logger.debug("  - Sample Google: %s", json.dumps(preview_google, ensure_ascii=False))

        # 1. Calculate the detailed, quantitative metrics
        advanced_metrics = calculate_advanced_metrics(solr_formatted, google_formatted)

        # Metrics summary
        logger.info(
            "  - Metrics: precision_ratio=%.4f | MRR=%.4f",
            advanced_metrics.get("precision_ratio", 0) or 0.0,
            advanced_metrics.get("mean_reciprocal_rank", 0) or 0.0,
        )
        if verbose:
            cov = advanced_metrics.get("coverage_per_google_poi", {}) or {}
            if cov:
                # show a small preview of coverage dictionary
                cov_items = list(cov.items())[:3]
                cov_preview = {k: v for k, v in cov_items}
                logger.debug("      coverage_preview: %s", json.dumps(cov_preview, ensure_ascii=False))

        # 2. Perform the final AI-based holistic judgment
        holistic_judgment = evaluate_holistic_set(query, solr_formatted, google_formatted)
        logger.info("  - Holistic AI score=%s", holistic_judgment.get("score"))

        # Rate limit between LLM-backed requests to ~20 req/min (3s gap)
        time.sleep(4)

        # 3. Combine everything into a comprehensive report for this query
        final_report.append({
            "query": query,
            "holistic_ai_score": holistic_judgment.get("score"),
            "holistic_ai_reasoning": holistic_judgment.get("reasoning"),
            "quantitative_metrics": advanced_metrics,
            # Keep only counts (omit raw result arrays to reduce file size/noise)
            "raw_results": {
                "solr_count": len(solr_formatted),
                "google_count": len(google_formatted)
            }
        })

        # Save progress incrementally
        with open(output_path, "w", encoding="utf-8") as f:
            for item in final_report:
                f.write(json.dumps(item, indent=4) + "\n")

        if verbose:
            logger.debug("  - Progress: written %d records so far", len(final_report))

    logger.info("--- Evaluation Complete ---")
    logger.info(f"Saved detailed, advanced evaluation report to: {output_path}")

if __name__ == "__main__":
    main()
