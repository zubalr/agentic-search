# src/scripts/evaluation/run_evaluation.py

import os
import json
import logging
import time
from tqdm import tqdm
from typing import List, Dict, Any

# Import only the holistic evaluation function (pair-wise disabled for now)
from src.core.evaluation import evaluate_holistic_set

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

# Deterministic, holistic-friendly advanced metrics using string similarity (no LLM pair-wise calls).
# Computes coverage per google POI, precision ratio, and MRR based on normalized token overlap.
import re
import unicodedata

def _normalize_text(s: Any) -> str:
    if not s:
        return ""
    if not isinstance(s, str):
        s = str(s)
    s = s.lower()
    # strip accents
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # keep alnum and spaces
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    # collapse spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _tokenize(s: str) -> List[str]:
    s = _normalize_text(s)
    return s.split() if s else []

def _jaccard(a_tokens: List[str], b_tokens: List[str]) -> float:
    if not a_tokens and not b_tokens:
        return 0.0
    a_set, b_set = set(a_tokens), set(b_tokens)
    union = a_set | b_set
    if not union:
        return 0.0
    inter = a_set & b_set
    return len(inter) / len(union)

def _containment(a: str, b: str) -> float:
    # simple containment bonus if one contains the other
    if not a or not b:
        return 0.0
    if a in b or b in a:
        # scaled by shorter/longer length ratio to avoid over-rewarding tiny substrings
        shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
        if len(longer) == 0:
            return 0.0
        return max(0.2, min(0.6, len(shorter) / len(longer)))
    return 0.0

def _best_similarity(solr_candidates: List[str], google_candidates: List[str]) -> float:
    best = 0.0
    for s in solr_candidates:
        ns = _normalize_text(s)
        s_tokens = _tokenize(ns)
        for g in google_candidates:
            ng = _normalize_text(g)
            g_tokens = _tokenize(ng)
            jac = _jaccard(s_tokens, g_tokens)
            bonus = _containment(ns, ng)
            score = min(1.0, jac + bonus)
            if score > best:
                best = score
    return best

def calculate_advanced_metrics(solr_list: List[Dict], google_list: List[Dict]) -> Dict[str, Any]:
    """
    Holistic-friendly metrics without pair-wise LLM calls.
    - coverage_per_google_poi: {google_main_text: {"score": best_similarity(0..1), "rank": best_rank or -1}}
    - precision_ratio: fraction of Solr items that match any Google with similarity >= threshold
    - mean_reciprocal_rank: average of 1/rank over google items that have a match above threshold
    Threshold can be tuned via env EVAL_SIM_THRESHOLD (default 0.6).
    """
    threshold = float(os.getenv("EVAL_SIM_THRESHOLD", "0.6"))

    # Early return if lists empty
    if not solr_list or not google_list:
        return {
            "coverage_per_google_poi": {},
            "precision_ratio": 0.0,
            "mean_reciprocal_rank": 0.0
        }

    # Build candidate strings for each solr entry (in ranked order)
    solr_candidates_per_item: List[List[str]] = []
    for r in solr_list:
        pn = r.get("poi_name") or ""
        cn = r.get("container") or ""
        candidates = []
        if pn:
            candidates.append(pn)
        if cn:
            candidates.append(cn)
        if pn or cn:
            candidates.append(f"{pn} {cn}".strip())
        # fallback to any non-empty fields if above are empty
        if not candidates:
            # try to concatenate all string values
            vals = [str(v) for v in r.values() if isinstance(v, (str, int, float))]
            if vals:
                candidates.append(" ".join(vals))
        solr_candidates_per_item.append([c for c in candidates if c])

    # Build candidate strings for each google entry
    google_candidates_per_item: List[List[str]] = []
    google_names: List[str] = []
    for g in google_list:
        mt = g.get("main_text") or ""
        st = g.get("secondary_text") or ""
        candidates = []
        if mt:
            candidates.append(mt)
        if st:
            candidates.append(st)
        if mt or st:
            candidates.append(f"{mt} {st}".strip())
        if not candidates:
            vals = [str(v) for v in g.values() if isinstance(v, (str, int, float))]
            if vals:
                candidates.append(" ".join(vals))
        google_candidates_per_item.append([c for c in candidates if c])
        google_names.append(mt or "Unknown Google POI")

    # Coverage and MRR
    coverage_report: Dict[str, Dict[str, Any]] = {}
    reciprocal_ranks: List[float] = []

    for gi, g_candidates in enumerate(google_candidates_per_item):
        best_score = -1.0
        best_rank = -1
        for si, s_candidates in enumerate(solr_candidates_per_item):
            sim = _best_similarity(s_candidates, g_candidates)
            if sim > best_score:
                best_score = sim
                best_rank = si + 1  # 1-based
        coverage_report[google_names[gi]] = {
            "score": round(max(0.0, best_score), 4),
            "rank": best_rank if best_score >= 0 else -1
        }
        if best_score >= threshold and best_rank > 0:
            reciprocal_ranks.append(1.0 / best_rank)

    # Precision: proportion of solr items that match any google above threshold
    relevant_solr = 0
    for s_candidates in solr_candidates_per_item:
        rel = False
        for g_candidates in google_candidates_per_item:
            sim = _best_similarity(s_candidates, g_candidates)
            if sim >= threshold:
                rel = True
                break
        if rel:
            relevant_solr += 1
    precision_ratio = relevant_solr / len(solr_candidates_per_item) if solr_candidates_per_item else 0.0
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0

    return {
        "coverage_per_google_poi": coverage_report,
        "precision_ratio": round(precision_ratio, 4),
        "mean_reciprocal_rank": round(mrr, 4)
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

    # Robust reader that supports both strict JSONL and a single JSON array file.
    # Strategy:
    # 1) Try fast JSONL streaming (line-by-line objects).
    # 2) If too many malformed lines, fallback to parsing the entire file as a JSON array.
    records = []
    malformed = 0
    total_lines = 0
    with open(input_path, "r", encoding="utf-8") as f:
        for idx, raw_line in enumerate(f, start=1):
            total_lines += 1
            line = raw_line.strip()
            # skip empty lines, comments, or separators often present in ad-hoc jsonl
            if not line or line.startswith("#") or line in {",", "[", "]"}:
                continue
            # handle trailing commas or accidental commas at end
            line = line.rstrip(",")
            # strip UTF-8 BOM if present
            if line and ord(line[0]) == 0xFEFF:
                line = line.lstrip("\ufeff")
            try:
                obj = json.loads(line)
                # validate expected keys to guard against partial fragments
                if isinstance(obj, dict) and ("query" in obj or "solr_results" in obj or "google_autocomplete_results" in obj):
                    records.append(obj)
                else:
                    # Not a full record; count as malformed to trigger fallback if pervasive
                    malformed += 1
            except json.JSONDecodeError as e:
                malformed += 1
                # Log only a sample of errors to avoid noisy logs
                if malformed <= 10:
                    logger.error("Malformed JSON at %s:%d: %s | line=%r", input_path, idx, str(e), raw_line)
                continue

    # Fallback: if more than 5 malformed lines OR zero parsed records, try reading as a single JSON array
    if malformed > 5 or not records:
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                file_text = f.read().strip()
            # Remove potential trailing commas in arrays/objects by a lenient approach:
            # - If file looks like an array, try to locate the outermost [ ... ] and json.loads it.
            if file_text.startswith("\ufeff"):
                file_text = file_text.lstrip("\ufeff")
            # Attempt direct parse
            parsed = json.loads(file_text)
            if isinstance(parsed, list):
                # Validate items are dict-like records
                filtered = []
                for i, item in enumerate(parsed, start=1):
                    if isinstance(item, dict) and ("query" in item or "solr_results" in item or "google_autocomplete_results" in item):
                        filtered.append(item)
                    else:
                        if i <= 10:
                            logger.debug("Skipping non-record element at array index %d", i)
                if filtered:
                    records = filtered
                    logger.info("Parsed input as a JSON array with %d records (fallback).", len(records))
                else:
                    logger.error("Parsed array contains no valid records. records=%d", len(filtered))
            else:
                logger.error("Fallback parse succeeded but top-level JSON is not an array. Type=%s", type(parsed).__name__)
        except Exception as e:
            logger.error("Failed fallback parse as JSON array: %s", str(e))

    if malformed:
        logger.info("Input parsing summary: total_lines=%d, parsed_records=%d, malformed_lines=%d", total_lines, len(records), malformed)

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

        # Rate limit between LLM-backed requests to ~15 req/min (4s gap)
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
