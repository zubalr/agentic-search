"""
Data I/O utilities for loading and saving search results and comparisons.
Refactored from the original data_io.py module.
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class DataIO:
    """Utility class for data input/output operations."""
    
    @staticmethod
    def load_jsonl_file(file_path: str) -> List[Dict[str, Any]]:
        """
        Load data from a JSONL file.
        
        Args:
            file_path: Path to the JSONL file
        
        Returns:
            List of dictionaries from the file
        """
        data = []
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        item = json.loads(line)
                        data.append(item)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Skipping malformed line {line_num} in {file_path}: {e}")
                        
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
        except Exception as e:
            logger.error(f"Error loading JSONL file {file_path}: {e}")
        
        logger.info(f"Loaded {len(data)} records from {file_path}")
        return data
    
    @staticmethod
    def save_jsonl_file(data: List[Dict[str, Any]], file_path: str, append: bool = False):
        """
        Save data to a JSONL file.
        
        Args:
            data: List of dictionaries to save
            file_path: Path to the output file
            append: Whether to append to existing file
        """
        # Ensure directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        mode = "a" if append else "w"
        
        try:
            with open(file_path, mode, encoding="utf-8") as f:
                for item in data:
                    f.write(json.dumps(item) + "\n")
            
            action = "Appended" if append else "Saved"
            logger.info(f"{action} {len(data)} records to {file_path}")
            
        except Exception as e:
            logger.error(f"Error saving JSONL file {file_path}: {e}")
    
    @staticmethod
    def load_search_results(file_path: str) -> Dict[str, Any]:
        """
        Load search results from JSONL file into a query-indexed dictionary.
        Aggregates Google POIs from text_search, nearby_search, and place_details if present.
        """
        results = {}
        try:
            data = DataIO.load_jsonl_file(file_path)
            is_google = "google" in file_path.lower() or "places" in file_path.lower()
            for item in data:
                if "query" in item:
                    # Handle different query formats
                    query = item["query"]
                    if isinstance(query, dict):
                        query = query.get("keyword", str(query))
                    if is_google:
                        # Aggregate all Google POIs
                        all_pois = []
                        ts = item.get('text_search', {})
                        ts_places = ts.get('places', []) if isinstance(ts, dict) else []
                        all_pois.extend(ts_places)
                        ns = item.get('nearby_search', {})
                        ns_places = ns.get('places', []) if isinstance(ns, dict) else []
                        all_pois.extend(ns_places)
                        pd = item.get('place_details', None)
                        if pd:
                            if isinstance(pd, list):
                                all_pois.extend(pd)
                            elif isinstance(pd, dict):
                                all_pois.append(pd)
                        results[query] = all_pois
                    else:
                        # Internal results
                        result = item.get("result", {})
                        results[query] = result
        except Exception as e:
            logger.error(f"Error processing search results from {file_path}: {e}")
        logger.info(f"Loaded search results for {len(results)} queries from {file_path}")
        return results
    
    @staticmethod
    def load_comparison_memory(file_path: str) -> Dict[str, Dict[str, Any]]:
        """
        Load existing comparisons from memory file to avoid re-processing.
        
        Args:
            file_path: Path to the comparison memory JSONL file
        
        Returns:
            Dictionary mapping query to comparison data
        """
        memory = {}
        
        if not os.path.exists(file_path):
            logger.info(f"Memory file {file_path} does not exist, starting fresh")
            return memory
        
        try:
            data = DataIO.load_jsonl_file(file_path)
            
            for item in data:
                if "query" in item:
                    query = item["query"]
                    comparison = item.get("comparison", item)  # Handle both formats
                    memory[query] = comparison
                    
        except Exception as e:
            logger.error(f"Error loading comparison memory from {file_path}: {e}")
        
        logger.info(f"Loaded comparison memory for {len(memory)} queries from {file_path}")
        return memory
    
    @staticmethod
    def save_comparison(file_path: str, query: str, comparison: Dict[str, Any]):
        """
        Save a single comparison to the memory file.
        
        Args:
            file_path: Path to the memory file
            query: Query string
            comparison: Comparison result dictionary
        """
        # Ensure directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                record = {"query": query, "comparison": comparison}
                f.write(json.dumps(record) + "\n")
            
            logger.debug(f"Saved comparison for query: {query}")
            
        except Exception as e:
            logger.error(f"Error saving comparison to {file_path}: {e}")
    
    @staticmethod
    def save_comparisons_batch(file_path: str, comparisons: List[Dict[str, Any]], append: bool = True):
        """
        Save multiple comparisons to file.
        
        Args:
            file_path: Path to the output file
            comparisons: List of comparison dictionaries
            append: Whether to append to existing file
        """
        # Ensure each comparison has the right format
        formatted_comparisons = []
        for comp in comparisons:
            if "query" in comp:
                formatted_comparisons.append(comp)
            else:
                # Assume the whole dict is the comparison and we need to extract query
                query = comp.get("query", "unknown")
                comparison_data = {k: v for k, v in comp.items() if k != "query"}
                formatted_comparisons.append({
                    "query": query,
                    "comparison": comparison_data
                })
        
        DataIO.save_jsonl_file(formatted_comparisons, file_path, append)
    
    @staticmethod
    def export_results_summary(comparisons: List[Dict[str, Any]], 
                             output_file: str,
                             format: str = "json") -> Dict[str, Any]:
        """
        Export a summary of comparison results.
        
        Args:
            comparisons: List of comparison results
            output_file: Path to the output file
            format: Output format ('json' or 'csv')
        
        Returns:
            Summary statistics
        """
        if not comparisons:
            logger.warning("No comparisons to export")
            return {}
        
        # Calculate summary statistics
        verdicts = [comp.get("verdict", "UNKNOWN") for comp in comparisons]
        verdict_counts = {}
        for verdict in verdicts:
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
        
        # Calculate average scores if available
        internal_scores = [comp.get("internal_server_score", 0) for comp in comparisons if comp.get("internal_server_score")]
        google_scores = [comp.get("google_maps_score", 0) for comp in comparisons if comp.get("google_maps_score")]
        
        summary = {
            "total_comparisons": len(comparisons),
            "verdict_distribution": verdict_counts,
            "average_internal_score": sum(internal_scores) / len(internal_scores) if internal_scores else 0,
            "average_google_score": sum(google_scores) / len(google_scores) if google_scores else 0,
        }
        
        # Save summary
        if format.lower() == "json":
            with open(output_file, 'w') as f:
                json.dump(summary, f, indent=2)
        elif format.lower() == "csv":
            # For CSV, export individual results
            import csv
            with open(output_file, 'w', newline='') as csvfile:
                if comparisons:
                    fieldnames = list(comparisons[0].keys())
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(comparisons)
        
        logger.info(f"Exported results summary to {output_file}")
        return summary
