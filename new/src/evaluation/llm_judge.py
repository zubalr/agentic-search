"""
LLM Judge evaluation using various language models.
Refactored for better modularity and integration.
"""

import os
import json
import logging
import asyncio
import traceback
from typing import List, Dict, Any, Optional, Literal
from dataclasses import dataclass

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from langchain_cerebras import ChatCerebras
from langchain_groq import ChatGroq

from src.core.evaluator import BaseEvaluatorInterface, EvaluationMode

logger = logging.getLogger(__name__)

# --- Pydantic Data Structure ---
class Comparison(BaseModel):
    """Data model for the comparison between two search results."""
    verdict: Literal["INTERNAL_SERVER_BETTER", "GOOGLE_MAPS_BETTER", "BOTH_ARE_GOOD", "BOTH_ARE_BAD", "INCONCLUSIVE"] = Field(description="The verdict.")
    reasoning: str = Field(description="A detailed, step-by-step explanation for the verdict.")
    internal_server_score: int = Field(description="A score from 1-5 for the internal server's result.", ge=1, le=5)
    google_maps_score: int = Field(description="A score from 1-5 for the Google Maps' result.", ge=1, le=5)

@dataclass
class ModelConfig:
    """Configuration for an LLM model."""
    provider: str
    model_name: str
    api_key: Optional[str] = None
    temperature: float = 0.0

class LLMManager:
    """
    Initialize and manage LLM clients for round-robin usage.
    Handles both Groq and Cerebras providers.
    """
    
    def __init__(self, model_configs: List[Dict[str, Any]]):
        self.clients = self._initialize_clients(model_configs)
        self.current_index = 0
        
        if not self.clients:
            raise ValueError("No LLM clients could be initialized. Check API keys and model configs.")
        
        logger.info(f"Initialized {len(self.clients)} LLM clients")

    def _initialize_clients(self, model_configs: List[Dict[str, Any]]) -> List:
        """Initialize LLM clients from configuration."""
        clients = []
        
        for config in model_configs:
            provider = config.get("provider")
            model_name = config.get("model_name")
            
            try:
                if provider == "groq":
                    api_key = config.get("api_key") or os.getenv("GROQ_API_KEY")
                    if api_key:
                        client = ChatGroq(
                            temperature=config.get("temperature", 0),
                            model_name=model_name,
                            groq_api_key=api_key
                        )
                        clients.append(client)
                        logger.info(f"Initialized Groq client with model: {model_name}")
                    else:
                        logger.warning(f"Skipping Groq model '{model_name}' due to missing API key")
                
                elif provider == "cerebras":
                    api_key = config.get("api_key") or os.getenv("CEREBRAS_API_KEY")
                    if api_key:
                        client = ChatCerebras(
                            model=model_name,
                            temperature=config.get("temperature", 0),
                            cerebras_api_key=api_key
                        )
                        clients.append(client)
                        logger.info(f"Initialized Cerebras client with model: {model_name}")
                    else:
                        logger.warning(f"Skipping Cerebras model '{model_name}' due to missing API key")
                
                else:
                    logger.warning(f"Unknown provider: {provider}")
            
            except Exception as e:
                logger.error(f"Failed to initialize LLM client for {provider}:{model_name}: {e}")
        
        return clients

    def get_next_client(self):
        """Return the next LLM client in round-robin fashion."""
        client = self.clients[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.clients)
        return client

    def get_client_info(self, client) -> str:
        """Get human-readable client information."""
        return getattr(client, "model_name", getattr(client, "model", "Unknown"))

# Evaluation prompt template
EVALUATION_PROMPT = ChatPromptTemplate.from_template(
    """
    You are an expert Search Quality Rater, focused on improving an internal search engine. Your primary goal is to evaluate how well search results match the user's query intent, prioritizing precision and relevance over anything else. Your evaluation must be objective, detailed, and based SOLELY on the data provided.

    **PRIMARY EVALUATION CRITERIA (Core Search Quality):**

    1.  **Precision & Top Result Accuracy (Most Important):**
        *   For a specific query like "Al Mirqab Mall", the #1 result MUST be "Al Mirqab Mall". Returning other popular malls first is a major failure.
        *   Score highly for exact top-result matches. Penalize heavily if the correct result is buried in the list or absent.

    2.  **Query Understanding & Component Handling:**
        *   For a multi-part query like "Al Noor compound thumama", the search engine MUST understand and use all components ("Al Noor compound" AND "thumama").
        *   A result set that only returns items for "Thumama" (e.g., "Al Thumama Stadium") and ignores "Al Noor compound" is a complete failure on this criterion.

    3.  **Result Set Relevance & Purity:**
        *   Are the results directly relevant to the user's intent?
        *   Penalize "noisy" results. For a query about a mall, results like "Gate Mall Parking" or "Al Sadd Street" are low-quality noise and should lower the score. The result set should be clean and focused on the entity type requested.

    **SECONDARY EVALUATION CRITERIA (Result Usefulness):**

    4.  **Information Completeness for User Action:**
        *   While the primary goal is finding the right place, a search result is only useful if it provides actionable information.
        *   Compare the completeness of the data provided for the POIs. A result set is considered higher quality if it includes essential, user-facing fields like a full `formattedAddress` and `contact` information.
        *   The presence of fields like `websiteUri`, `rating`, `userRatingCount`, and `currentOpeningHours` in one result set and their absence in the other makes the first set significantly more valuable to an end-user, even if it's not a direct search-matching metric. Acknowledge this difference in value.
        *   Internal metadata like `popularity` or `score` should be ignored as they provide no value to the end-user.

    **TASK:**
    Based on the criteria above, with a strong emphasis on the PRIMARY criteria, compare the 'Internal Server Result' and the 'Google Maps Result'. Provide a verdict, a detailed step-by-step reasoning for your decision, and a 1-5 score for each result set. Your entire response MUST be a single JSON object that conforms to the provided schema. Do not include any text outside the JSON object.

    **JSON SCHEMA:**
    {schema}

    **QUERY:**
    "{query}"

    **INTERNAL SERVER RESULT (JSON):**
    {internal_results}

    **GOOGLE MAPS RESULT (JSON):**
    {google_results}
    
    **AUTOMATED METRICS (for context only):**
    {comparison_summary}
    """
)

class LLMJudgeEvaluator(BaseEvaluatorInterface):
    """LLM-based evaluator for comparing search results."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.llm_manager = None
        self.parser = JsonOutputParser(pydantic_object=Comparison)
        self._initialize_llm_manager()
    
    def _initialize_llm_manager(self):
        """Initialize the LLM manager with configured models."""
        model_configs = self.config.get('llm_models', self._get_default_models())
        self.llm_manager = LLMManager(model_configs)
    
    def _get_default_models(self) -> List[Dict[str, Any]]:
        """Get default model configuration."""
        return [
            {"provider": "cerebras", "model_name": "llama-3.3-70b"},
            {"provider": "groq", "model_name": "llama-3.3-70b-versatile"}
        ]
    
    async def judge_single_query(self, 
                               query: str, 
                               internal_result: Dict[str, Any], 
                               google_result: Dict[str, Any],
                               comparison_summary: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Process a single query and return the LLM's comparison result.
        
        Args:
            query: Search query string
            internal_result: Result from internal API
            google_result: Result from Google Places API
            comparison_summary: Dict of computed metrics and diffs
        
        Returns:
            Comparison result or None if error occurs
        """
        if not internal_result or not google_result:
            logger.warning(f"One of the results for query '{query}' is empty. Skipping.")
            return None
        
        llm_client = self.llm_manager.get_next_client()
        model_identifier = self.llm_manager.get_client_info(llm_client)
        logger.info(f"Processing '{query}' using model '{model_identifier}'")
        
        try:
            # Add comparison summary to prompt context
            prompt_vars = {
                "query": query,
                "internal_results": json.dumps(internal_result, indent=2),
                "google_results": json.dumps(google_result, indent=2),
                "schema": Comparison.schema_json(indent=2),
                "comparison_summary": json.dumps(comparison_summary, indent=2) if comparison_summary else "Not available."
            }

            chain = EVALUATION_PROMPT | llm_client | self.parser
            comparison_result = await chain.ainvoke(prompt_vars)
            
            verdict = comparison_result.get('verdict', 'N/A')
            logger.info(f"Verdict for '{query}': {verdict}")
            
            # Add metadata
            comparison_result["query"] = query
            comparison_result["model"] = model_identifier
            
            return comparison_result
        
        except Exception as e:
            logger.error(f"Error processing query '{query}': {e}\\n{traceback.format_exc()}")
            return None
    
    async def evaluate_batch(self, 
                           queries_data: Dict[str, tuple], 
                           batch_size: int = 5,
                           delay_between_batches: float = 10.0) -> List[Dict[str, Any]]:
        """
        Evaluate queries in batches with rate limiting.
        
        Args:
            queries_data: Dict mapping query -> (internal_result, google_result)
            batch_size: Number of queries to process concurrently
            delay_between_batches: Delay between batches in seconds
        
        Returns:
            List of comparison results
        """
        results = []
        queries = list(queries_data.keys())
        total_queries = len(queries)
        
        logger.info(f"Starting batch evaluation for {total_queries} queries...")
        
        for i in range(0, total_queries, batch_size):
            batch_queries = queries[i:i + batch_size]
            batch_tasks = []
            
            for query in batch_queries:
                internal_result, google_result = queries_data[query]
                task = self.judge_single_query(query, internal_result, google_result)
                batch_tasks.append(task)
            
            # Process batch concurrently
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Filter out None results and exceptions
            for result in batch_results:
                if isinstance(result, dict):
                    results.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Batch processing error: {result}")
            
            # Progress logging
            processed = min(i + batch_size, total_queries)
            logger.info(f"Processed {processed}/{total_queries} queries")
            
            # Delay between batches (except for the last batch)
            if i + batch_size < total_queries:
                logger.info(f"Waiting {delay_between_batches} seconds before next batch...")
                await asyncio.sleep(delay_between_batches)
        
        logger.info(f"Batch evaluation completed. Generated {len(results)} results.")
        return results
    
    async def evaluate_sequential(self, 
                                queries_data: Dict[str, tuple],
                                delay_between_queries: float = 2.0) -> List[Dict[str, Any]]:
        """
        Evaluate queries sequentially with delay between each.
        
        Args:
            queries_data: Dict mapping query -> (internal_result, google_result)
            delay_between_queries: Delay between queries in seconds
        
        Returns:
            List of comparison results
        """
        results = []
        queries = list(queries_data.keys())
        total_queries = len(queries)
        
        logger.info(f"Starting sequential evaluation for {total_queries} queries...")
        
        for i, query in enumerate(queries, 1):
            internal_result, google_result = queries_data[query]
            result = await self.judge_single_query(query, internal_result, google_result)
            
            if result:
                results.append(result)
            
            logger.info(f"Processed {i}/{total_queries} queries")
            
            # Delay between queries (except for the last query)
            if i < total_queries:
                await asyncio.sleep(delay_between_queries)
        
        logger.info(f"Sequential evaluation completed. Generated {len(results)} results.")
        return results
    
    def evaluate(self, 
                internal_results: Dict[str, Any],
                google_results: Dict[str, Any],
                mode: EvaluationMode,
                **kwargs) -> Dict[str, Any]:
        """
        Main evaluation method implementing BaseEvaluatorInterface.
        
        Args:
            internal_results: Results from internal API
            google_results: Results from Google Places API
            mode: Evaluation mode (batch or sequential)
            **kwargs: Additional arguments
        
        Returns:
            Evaluation results
        """
        # Prepare queries data
        queries_data = {}
        for query in internal_results:
            if query in google_results:
                queries_data[query] = (internal_results[query], google_results[query])
        
        # Extract parameters
        batch_size = kwargs.get('batch_size', 5)
        delay_between_batches = kwargs.get('delay_between_batches', 10.0)
        delay_between_queries = kwargs.get('delay_between_queries', 2.0)
        
        # Run evaluation based on mode
        if mode == EvaluationMode.BATCH:
            results = asyncio.run(self.evaluate_batch(
                queries_data, batch_size, delay_between_batches
            ))
        else:
            results = asyncio.run(self.evaluate_sequential(
                queries_data, delay_between_queries
            ))
        
        return {
            "evaluation_method": "llm_judge",
            "mode": mode.value,
            "total_queries": len(queries_data),
            "successful_evaluations": len(results),
            "results": results
        }
    
    def get_metrics(self) -> List[str]:
        """Get list of metrics this evaluator provides."""
        return [
            "verdict",
            "internal_server_score",
            "google_maps_score",
            "reasoning"
        ]
