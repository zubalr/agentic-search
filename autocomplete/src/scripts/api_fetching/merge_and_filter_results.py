#!/usr/bin/env python3
"""
Script to filter specific fields from Solr and Google Autocomplete API results
and merge them into a single consolidated file, with one line per query.
"""

import json
import argparse
from pathlib import Path
import logging
from collections import defaultdict
from ...core.api_client import load_queries_from_csv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_solr_data(solr_file_path, aggregated_solr_data):
    """Extracts name, poiName, and containerName from a Solr results JSONL file and aggregates by query."""
    try:
        with open(solr_file_path, 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    query = data.get("query", {}).get("keyword", "N/A")
                    results_list = data.get("result", [])
                    
                    if not isinstance(results_list, list):
                        logger.warning(f"Line {line_number} in {solr_file_path}: 'result' is not a list. Skipping line for query: {query}")
                        continue

                    for result_item in results_list:
                        filtered_entry = {
                            "solr_name": result_item.get("name"),
                            "solr_poiName": result_item.get("poiName"),
                            "solr_containerName": result_item.get("containerName"),
                        }
                        aggregated_solr_data[query].append(filtered_entry)
                except json.JSONDecodeError:
                    logger.warning(f"Could not decode JSON line {line_number} in {solr_file_path}: {line.strip()}")
                except Exception as e:
                    logger.error(f"Error processing line {line_number} in {solr_file_path}: {e}")
    except FileNotFoundError:
        logger.error(f"Solr file not found: {solr_file_path}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while reading {solr_file_path}: {e}")

def extract_google_autocomplete_data(google_file_path, aggregated_google_data):
    """Extracts specific prediction texts from a Google Autocomplete results JSONL file and aggregates by query."""
    debug_log_count = 0 # Log details for the first 5 non-empty structuredFormat objects
    try:
        with open(google_file_path, 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    query = data.get("query", "N/A")
                    response = data.get("response", {})
                    suggestions = response.get("suggestions", [])

                    for suggestion_idx, suggestion in enumerate(suggestions):
                        place_prediction = suggestion.get("placePrediction", {}) or {}
                        # structuredFormat is nested under placePrediction (not a sibling)
                        structured_format = place_prediction.get("structuredFormat", {}) or {}
                        
                        # --- Targeted Debug Logging ---
                        if structured_format and debug_log_count < 5:
                            logger.info(f"DEBUG_FOUND - Query: {query}, Suggestion Index: {suggestion_idx}")
                            logger.info(f"DEBUG_FOUND - Raw structured_format: {json.dumps(structured_format)}")
                            main_text_val = (structured_format.get("mainText") or {}).get("text")
                            secondary_text_val = (structured_format.get("secondaryText") or {}).get("text")
                            logger.info(f"DEBUG_FOUND - Extracted main_text: {main_text_val}")
                            logger.info(f"DEBUG_FOUND - Extracted secondary_text: {secondary_text_val}")
                            logger.info("--------------------------------------------------")
                            debug_log_count += 1
                        # --- End Debug Logging ---

                        filtered_entry = {
                            "google_place_prediction_text": (place_prediction.get("text") or {}).get("text"),
                            "google_main_text": (structured_format.get("mainText") or {}).get("text"),
                            "google_secondary_text": (structured_format.get("secondaryText") or {}).get("text"),
                        }
                        aggregated_google_data[query].append(filtered_entry)
                except json.JSONDecodeError:
                    logger.warning(f"Could not decode JSON line {line_number} in {google_file_path}: {line.strip()}")
                except Exception as e:
                    logger.error(f"Error processing line {line_number} in {google_file_path}: {e}")
    except FileNotFoundError:
        logger.error(f"Google Autocomplete file not found: {google_file_path}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while reading {google_file_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Filter and merge Solr and Google Autocomplete API results into one line per query.')
    parser.add_argument('--raw-dir', default='raw', help='Directory containing raw API result files (default: raw)')
    parser.add_argument('--output-file', default='data/results/merged_filtered_results.jsonl', help='Output file for merged results (default: data/results/merged_filtered_results.jsonl)')
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    output_file = Path(args.output_file)

    if not raw_dir.is_dir():
        logger.error(f"Raw directory not found: {raw_dir}")
        return

    aggregated_solr_data = defaultdict(list)
    aggregated_google_data = defaultdict(list)

    # Process Solr files
    solr_files = sorted(list(raw_dir.glob("api_results_solr_*.jsonl")))
    logger.info(f"Found {len(solr_files)} Solr result files to process.")
    for solr_file in solr_files:
        logger.info(f"Processing Solr file: {solr_file.name}")
        extract_solr_data(solr_file, aggregated_solr_data)
        logger.info(f"Finished processing {solr_file.name}. Total unique Solr queries so far: {len(aggregated_solr_data)}")

    # Process Google Autocomplete files
    google_files = sorted(list(raw_dir.glob("google_autocomplete_results_*.jsonl")))
    logger.info(f"Found {len(google_files)} Google Autocomplete result files to process.")
    for google_file in google_files:
        logger.info(f"Processing Google Autocomplete file: {google_file.name}")
        extract_google_autocomplete_data(google_file, aggregated_google_data)
        logger.info(f"Finished processing {google_file.name}. Total unique Google queries so far: {len(aggregated_google_data)}")

    if not aggregated_solr_data and not aggregated_google_data:
        logger.warning("No data was extracted from any files. Output file will not be created.")
        return

    # Get all unique queries from both sources, sort them for consistent output
    all_queries = sorted(set(aggregated_solr_data.keys()) | set(aggregated_google_data.keys()))
    logger.info(f"Total unique queries to merge: {len(all_queries)}")

    # Write merged data to output file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for query in all_queries:
                merged_entry = {
                    "query": query,
                    "solr_results": aggregated_solr_data.get(query, []),
                    "google_autocomplete_results": aggregated_google_data.get(query, [])
                }
                f.write(json.dumps(merged_entry) + '\n')
        logger.info(f"Successfully merged {len(all_queries)} queries into {output_file}")
    except Exception as e:
        logger.error(f"Failed to write output file {output_file}: {e}")

if __name__ == '__main__':
    main()
