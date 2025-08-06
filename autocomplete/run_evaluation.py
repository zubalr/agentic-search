# run_evaluation.py

import os
import json
import pandas as pd
from dotenv import load_dotenv
from eval_pipeline import evaluate_poi_relevancy

# Load API keys and settings from .env file early so deepeval/litellm can pick them up
load_dotenv()


def main():
    """
    Main function to run the full evaluation pipeline.
    Ensures the required env vars exist, builds a sample dataset, evaluates, and prints a report.
    """

    # --- 0. Validate Environment ---
    cerebras_key = os.getenv("CEREBRAS_API_KEY")
    if not cerebras_key:
        print("ERROR: CEREBRAS_API_KEY is not set. Copy .env.example to .env and fill in your key.")
        return

    model = os.getenv("LITELLM_MODEL", "cerebras/llama3.3-70b")
    print(f"Using litellm model: {model}")

    # --- 1. Load Your Data ---
    # Read real merged JSON produced by your pipeline (file appears to be a single JSON array)
    input_path = os.getenv("EVAL_INPUT_PATH", "merged_filtered_results.jsonl")
    if not os.path.exists(input_path):
        print(f"ERROR: Input file not found: {input_path}")
        print("Set EVAL_INPUT_PATH in .env if your file is elsewhere.")
        return

    # Detect whether the file starts with '[' (JSON array) or line-delimited JSON (JSONL)
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            print(f"ERROR: Input file is empty: {input_path}")
            return

        # Some editors may add shell prompt noise at the top; strip leading junk until '[' or '{'
        first_bracket_pos = min(
            [pos for pos in [content.find("["), content.find("{")] if pos != -1] or [0]
        )
        if first_bracket_pos > 0:
            content = content[first_bracket_pos:].lstrip()

        # Try parse as a single JSON array first
        if content.startswith("["):
            try:
                records = json.loads(content)
            except json.JSONDecodeError:
                # Fallback: try line-delimited JSON parsing
                records = []
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line == "[" or line == "]" or line == ",":
                        continue
                    try:
                        obj = json.loads(line.rstrip(","))
                        records.append(obj)
                    except json.JSONDecodeError:
                        continue
        else:
            # Not an array; try JSONL
            records = []
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line.rstrip(","))
                    records.append(obj)
                except json.JSONDecodeError:
                    continue

    if not records:
        print(f"ERROR: No valid JSON objects parsed from {input_path}")
        return

    # Map fields from your merged structure to expected columns.
    # Adjust keys if your merged file uses different names.
    def safe_get(d, *path, default=""):
        cur = d
        for p in path:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                return default
        return cur

    data_rows = []
    for obj in records:
        query = obj.get("query", "")

        # Your file shows arrays of top-k results. We'll take the top-1 from each as representative.
        solr_list = obj.get("solr_results") or obj.get("solr") or []
        google_list = obj.get("google_results") or obj.get("google") or []

        solr_top = solr_list[0] if isinstance(solr_list, list) and solr_list else {}
        google_top = google_list[0] if isinstance(google_list, list) and google_list else {}

        # Primary mapping from nested top-1 items
        solr_name = solr_top.get("solr_name", "")
        solr_poi_name = solr_top.get("solr_poiName", "")
        solr_container_name = solr_top.get("solr_containerName", "")

        g_main = google_top.get("google_main_text", "") or google_top.get("main_text", "")
        g_secondary = google_top.get("google_secondary_text", "") or google_top.get("secondary_text", "")
        g_full = google_top.get("google_place_prediction_text", "") or google_top.get("prediction_text", "")

        # Fallbacks: try top-level alternative keys if nested keys are missing
        if not solr_name:
            solr_name = obj.get("solr_name", "")
        if not solr_poi_name:
            solr_poi_name = obj.get("solr_poiName", "")
        if not solr_container_name:
            solr_container_name = obj.get("solr_containerName", "")

        if not g_full:
            g_full = obj.get("google_place_prediction_text", "")
        if not g_main:
            g_main = obj.get("google_main_text", "")
        if not g_secondary:
            g_secondary = obj.get("google_secondary_text", "")

        data_rows.append(
            {
                "query": query,
                "solr_name": solr_name,
                "solr_poiName": solr_poi_name,
                "solr_containerName": solr_container_name,
                "google_place_prediction_text": g_full,
                "google_main_text": g_main,
                "google_secondary_text": g_secondary,
            }
        )

    df = pd.DataFrame(data_rows)
    if df.empty:
        print("ERROR: Constructed DataFrame is empty after mapping.")
        return

    # Optional: limit rows via env to control cost during trial runs
    limit = os.getenv("EVAL_ROW_LIMIT")
    if limit:
        try:
            n = int(limit)
            df = df.head(n)
            print(f"Limiting evaluation to first {n} rows (EVAL_ROW_LIMIT).")
        except ValueError:
            pass

    # --- 2. Run Evaluation Loop ---
    results = []
    for _, row in df.iterrows():
        print(f"Evaluating query: '{row['query']}'...")

        solr_result = {
            "solr_name": row["solr_name"],
            "solr_poiName": row["solr_poiName"],
            "solr_containerName": row["solr_containerName"],
        }

        google_result = {
            "google_place_prediction_text": row["google_place_prediction_text"],
            "google_main_text": row["google_main_text"],
            "google_secondary_text": row["google_secondary_text"],
        }

        eval_result = evaluate_poi_relevancy(solr_result, google_result)

        results.append(
            {
                "query": row["query"],
                "score": eval_result["score"],
                "reasoning": eval_result["reasoning"],
            }
        )

    # --- 3. Aggregate and Display Results ---
    results_df = pd.DataFrame(results)
    average_score = results_df["score"].mean()

    # Save outputs
    output_csv = os.getenv("EVAL_OUTPUT_CSV", "evaluation_results.csv")
    output_jsonl = os.getenv("EVAL_OUTPUT_JSONL", "evaluation_results.jsonl")
    summary_txt = os.getenv("EVAL_SUMMARY_TXT", "evaluation_summary.txt")

    # Persist detailed rows
    try:
        results_df.to_csv(output_csv, index=False)
    except Exception as e:
        print(f"WARNING: Failed to write CSV {output_csv}: {e}")

    try:
        with open(output_jsonl, "w", encoding="utf-8") as f:
            for rec in results:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"WARNING: Failed to write JSONL {output_jsonl}: {e}")

    # Persist summary
    try:
        with open(summary_txt, "w", encoding="utf-8") as f:
            f.write("--- Evaluation Summary ---\n")
            f.write(f"Overall Average Score: {average_score:.2f} / 10\n")
            f.write(f"Rows Evaluated: {len(results_df)}\n")
            f.write(f"Model: {model}\n")
            f.write(f"Input: {input_path}\n")
            if limit:
                f.write(f"Row Limit: {limit}\n")
    except Exception as e:
        print(f"WARNING: Failed to write summary {summary_txt}: {e}")

    print("\n--- Evaluation Complete ---")
    print(f"\nOverall Average Score: {average_score:.2f} / 10")
    print(f"Saved detailed results to: {output_csv} and {output_jsonl}")
    print(f"Saved summary to: {summary_txt}")

    print("\n--- Detailed Results (first 20) ---")
    print(results_df.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
