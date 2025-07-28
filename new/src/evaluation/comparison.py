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
                
                task = self.evaluator.judge_single_query(query, internal_result, google_result)
                batch_tasks.append(task)
            
            # Process batch concurrently
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process results
            for result in batch_results:
                if isinstance(result, dict):
                    all_results.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Batch processing error: {result}")
            
            # Progress logging
            processed = min(i + batch_size, len(queries_to_process))
            logger.info(f"Completed {processed}/{len(queries_to_process)} queries")
            
            # Delay between batches (except for the last batch)
            if i + batch_size < len(queries_to_process):
                logger.info(f"Waiting {delay_between_batches} seconds before next batch...")
                await asyncio.sleep(delay_between_batches)
        
        logger.info(f"Batch processing completed. Generated {len(all_results)} comparison results.")
        return all_results
    
    async def process_queries_sequential(self, 
                                       internal_results: Dict[str, Any],
                                       google_results: Dict[str, Any],
                                       delay_between_queries: float = 2.0,
                                       skip_processed: bool = True,
                                       comparison_memory: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Process all queries sequentially with delay between each.
        
        Args:
            internal_results: Results from internal API
            google_results: Results from Google Places API
            delay_between_queries: Delay between queries in seconds
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
        
        logger.info(f"Processing {len(queries_to_process)} queries sequentially")
        
        all_results = []
        
        for idx, query in enumerate(queries_to_process):
            logger.info(f"Processing query {idx + 1}/{len(queries_to_process)}: {query}")
            
            internal_result = internal_results[query]
            google_result = google_results[query]
            
            result = await self.evaluator.judge_single_query(query, internal_result, google_result)
            
            if result:
                all_results.append(result)
            
            # Delay between queries (except for the last query)
            if idx + 1 < len(queries_to_process):
                await asyncio.sleep(delay_between_queries)
        
        logger.info(f"Sequential processing completed. Generated {len(all_results)} comparison results.")
        return all_results
    
    async def compare_results(self,
                            internal_results: Dict[str, Any],
                            google_results: Dict[str, Any],
                            mode: EvaluationMode = EvaluationMode.BATCH,
                            **kwargs) -> Dict[str, Any]:
        """
        Main comparison method that delegates to batch or sequential processing.
        
        Args:
            internal_results: Results from internal API
            google_results: Results from Google Places API
            mode: Processing mode (batch or sequential)
            **kwargs: Additional arguments for specific modes
        
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
