"""
Comparison engine for orchestrating result comparisons.
Refactored from the original compare.py module.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional

from src.core.evaluator import EvaluationMode
from .llm_judge import LLMJudgeEvaluator

logger = logging.getLogger(__name__)

class ComparisonEngine:
    """
    Main orchestration logic for comparing search results.
    Provides batch and sequential processing modes.
    """
    
    def __init__(self, evaluator: Optional[LLMJudgeEvaluator] = None):
        self.evaluator = evaluator or LLMJudgeEvaluator()
    
    async def process_queries_batch(self, 
                                  internal_results: Dict[str, Any],
                                  google_results: Dict[str, Any],
                                  batch_size: int = 5,
                                  delay_between_batches: float = 10.0,
                                  skip_processed: bool = True,
                                  comparison_memory: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Process all queries in batches with concurrent execution.
        
        Args:
            internal_results: Results from internal API
            google_results: Results from Google Places API
            batch_size: Number of queries to process concurrently
            delay_between_batches: Delay between batches in seconds
            skip_processed: Whether to skip already processed queries
            comparison_memory: Previously processed comparisons
        
        Returns:
            List of comparison results
        """
        comparison_memory = comparison_memory or {}
        
        # Filter queries to process
        if skip_processed:
            queries_to_process = [
                q for q in internal_results 
                if q not in comparison_memory and q in google_results
            ]
        else:
            queries_to_process = [
                q for q in internal_results 
                if q in google_results
            ]
        
        logger.info(f"Processing {len(queries_to_process)} queries in batches of {batch_size}")
        all_results = []
        for i in range(0, len(queries_to_process), batch_size):
            batch_queries = queries_to_process[i:i + batch_size]
            batch_tasks = []
            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch_queries)} queries")
            for query in batch_queries:
                internal_result = internal_results[query]
                google_result = google_results[query]
                def get_poi_ids(results):
                    return set([str(poi.get('entryId', poi.get('name', ''))) for poi in results if isinstance(poi, dict)])
                internal_pois = internal_result if isinstance(internal_result, list) else []
                google_pois = google_result if isinstance(google_result, list) else []
                internal_ids = get_poi_ids(internal_pois)
                google_ids = get_poi_ids(google_pois)
                exact_match = internal_ids == google_ids
                intersection = internal_ids & google_ids
                union = internal_ids | google_ids
                jaccard = len(intersection) / len(union) if union else 0.0
                N = min(5, len(internal_pois), len(google_pois))
                top_internal = [str(poi.get('entryId', poi.get('name', ''))) for poi in internal_pois[:N]]
                top_google = [str(poi.get('entryId', poi.get('name', ''))) for poi in google_pois[:N]]
                top_overlap = len(set(top_internal) & set(top_google)) / N if N else 0.0
                missing_in_google = list(internal_ids - google_ids)
                missing_in_internal = list(google_ids - internal_ids)
                field_diffs = []
                for poi_id in intersection:
                    poi_internal = next((poi for poi in internal_pois if str(poi.get('entryId', poi.get('name', ''))) == poi_id), None)
                    poi_google = next((poi for poi in google_pois if str(poi.get('entryId', poi.get('name', ''))) == poi_id), None)
                    if poi_internal and poi_google:
                        diff = {k: (poi_internal.get(k), poi_google.get(k)) for k in set(poi_internal.keys()) | set(poi_google.keys()) if poi_internal.get(k) != poi_google.get(k)}
                        field_diffs.append({'poi_id': poi_id, 'diff': diff})
                true_positives = len(intersection)
                false_positives = len(internal_ids - google_ids)
                false_negatives = len(google_ids - internal_ids)
                precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
                recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
                f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
                comparison_summary = {
                    'exact_match': exact_match,
                    'jaccard_similarity': jaccard,
                    'top_overlap': top_overlap,
                    'missing_in_google': missing_in_google,
                    'missing_in_internal': missing_in_internal,
                    'field_diffs': field_diffs,
                    'precision': precision,
                    'recall': recall,
                    'f1': f1,
                }
                task = self.evaluator.judge_single_query(
                    query,
                    internal_result,
                    google_result,
                    comparison_summary=comparison_summary
                )
                batch_tasks.append(task)
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            for result in batch_results:
                if isinstance(result, dict):
                    all_results.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Batch processing error: {result}")
            processed = min(i + batch_size, len(queries_to_process))
            logger.info(f"Completed {processed}/{len(queries_to_process)} queries")
            if i + batch_size < len(queries_to_process):
                logger.info(f"Waiting {delay_between_batches} seconds before next batch...")
                await asyncio.sleep(delay_between_batches)
        logger.info(f"Batch processing completed. Generated {len(all_results)} comparison results.")
        return all_results
        
        logger.info(f"Processing {len(queries_to_process)} queries sequentially")
        
        all_results = []
        
        for idx, query in enumerate(queries_to_process):
            logger.info(f"Processing query {idx + 1}/{len(queries_to_process)}: {query}")
            
            internal_result = internal_results[query]
            google_result = google_results[query]
            
            result = await self.evaluator.judge_single_query(query, internal_result, google_result)
            
            if result:
                all_results.append(result)
                # Automated metrics: precision, recall, F1
                true_positives = len(intersection)
                false_positives = len(internal_ids - google_ids)
                false_negatives = len(google_ids - internal_ids)
                precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
                recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
                f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
            
            # Delay between queries (except for the last query)
                comparison_summary = {
                    'exact_match': exact_match,
                    'jaccard_similarity': jaccard,
                    'top_overlap': top_overlap,
                    'missing_in_google': missing_in_google,
                    'missing_in_internal': missing_in_internal,
                    'field_diffs': field_diffs,
                    'precision': precision,
                    'recall': recall,
                    'f1': f1,
                }

    async def compare_results(
        self,
        internal_results: Dict[str, Any],
        google_results: Dict[str, Any],
        mode: EvaluationMode = EvaluationMode.BATCH,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Main comparison method that delegates to batch or sequential processing.
        
        Args:
            internal_results: Results from internal API
            google_results: Results from Google Places API
            mode: Processing mode (batch or sequential)
            **kwargs: Additional arguments for specific modes
        
        """
        """
        if mode == EvaluationMode.BATCH:
            results = await self.process_queries_batch(
                internal_results,
                google_results,
                **kwargs
            )
        else:
            results = await self.process_queries_sequential(
                internal_results,
                google_results,
                **kwargs
            )
        return {
            "mode": mode.value,
            "total_internal_queries": len(internal_results),
            "total_google_queries": len(google_results),
            "processed_queries": len(results),
            "results": results
        }
        
        Returns:
            Comparison results with metadata
        """
        if mode == EvaluationMode.BATCH:
            results = await self.process_queries_batch(
                internal_results, 
                google_results,
                **kwargs
            )
        else:
            results = await self.process_queries_sequential(
                internal_results, 
                google_results,
                **kwargs
            )
        
        return {
            "mode": mode.value,
            "total_internal_queries": len(internal_results),
            "total_google_queries": len(google_results),
            "processed_queries": len(results),
            "results": results
        }


def create_comparison_engine(config: Optional[Dict[str, Any]] = None) -> ComparisonEngine:
    """
    Factory function to create a comparison engine with configured evaluator.
    Args:
        config: Configuration for the evaluator
    Returns:
        Configured ComparisonEngine instance
    """
    evaluator = LLMJudgeEvaluator(config)
    return ComparisonEngine(evaluator)
