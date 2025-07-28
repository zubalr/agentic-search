"""
Data models and schemas for the agentic search system.
"""

from typing import Dict, List, Any, Optional, Literal
from dataclasses import dataclass
from datetime import datetime

@dataclass
class SearchQuery:
    """Represents a search query with optional location."""
    keyword: str
    lat: Optional[str] = None
    lng: Optional[str] = None
    timestamp: Optional[datetime] = None

@dataclass
class SearchResult:
    """Represents a search result from any API."""
    query: SearchQuery
    results: List[Dict[str, Any]]
    source: str  # 'solr', 'google_places', etc.
    total_results: int = 0
    response_time: Optional[float] = None
    error: Optional[str] = None
    success: bool = True

@dataclass
class ComparisonResult:
    """Represents a comparison between two search results."""
    query: str
    verdict: Literal["INTERNAL_SERVER_BETTER", "GOOGLE_MAPS_BETTER", "BOTH_ARE_GOOD", "BOTH_ARE_BAD", "INCONCLUSIVE"]
    reasoning: str
    internal_server_score: int  # 1-5
    google_maps_score: int  # 1-5
    model: Optional[str] = None
    timestamp: Optional[datetime] = None

@dataclass
class EvaluationMetrics:
    """Represents evaluation metrics for a set of comparisons."""
    total_comparisons: int
    verdict_distribution: Dict[str, int]
    average_internal_score: float
    average_google_score: float
    evaluation_method: str
    model_used: Optional[str] = None

@dataclass
class ProcessingConfig:
    """Configuration for processing operations."""
    batch_size: int = 5
    delay_between_batches: float = 10.0
    max_retries: int = 3
    timeout: int = 30
    
    # File paths
    internal_results_file: str = "api_results_solr.jsonl"
    google_results_file: str = "google_places_results.jsonl"
    comparison_memory_file: str = "comparison_memory.jsonl"
    failed_queries_file: str = "failed_queries.txt"
    
    # LLM configuration
    llm_models: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.llm_models is None:
            self.llm_models = [
                {"provider": "cerebras", "model_name": "llama-3.3-70b"}
            ]

class ResultValidator:
    """Utility class for validating data structures."""
    
    @staticmethod
    def validate_search_result(data: Dict[str, Any]) -> bool:
        """Validate if a dictionary represents a valid search result."""
        required_fields = ["query"]
        return all(field in data for field in required_fields)
    
    @staticmethod
    def validate_comparison_result(data: Dict[str, Any]) -> bool:
        """Validate if a dictionary represents a valid comparison result."""
        required_fields = ["query", "verdict", "reasoning"]
        valid_verdicts = [
            "INTERNAL_SERVER_BETTER", 
            "GOOGLE_MAPS_BETTER", 
            "BOTH_ARE_GOOD", 
            "BOTH_ARE_BAD", 
            "INCONCLUSIVE"
        ]
        
        if not all(field in data for field in required_fields):
            return False
        
        if data.get("verdict") not in valid_verdicts:
            return False
        
        # Validate scores if present
        for score_field in ["internal_server_score", "google_maps_score"]:
            if score_field in data:
                score = data[score_field]
                if not isinstance(score, int) or score < 1 or score > 5:
                    return False
        
        return True
    
    @staticmethod
    def normalize_query(query: Any) -> str:
        """Normalize different query formats to a string."""
        if isinstance(query, str):
            return query
        elif isinstance(query, dict):
            return query.get("keyword", str(query))
        else:
            return str(query)

def create_search_result_from_dict(data: Dict[str, Any]) -> Optional[SearchResult]:
    """Create a SearchResult object from a dictionary."""
    try:
        query_data = data.get("query", {})
        
        if isinstance(query_data, str):
            query = SearchQuery(keyword=query_data)
        elif isinstance(query_data, dict):
            query = SearchQuery(
                keyword=query_data.get("keyword", ""),
                lat=query_data.get("lat"),
                lng=query_data.get("lng")
            )
        else:
            query = SearchQuery(keyword=str(query_data))
        
        return SearchResult(
            query=query,
            results=data.get("result", []),
            source=data.get("source", "unknown"),
            total_results=len(data.get("result", [])),
            error=data.get("error"),
            success=data.get("error") is None
        )
    except Exception:
        return None

def create_comparison_result_from_dict(data: Dict[str, Any]) -> Optional[ComparisonResult]:
    """Create a ComparisonResult object from a dictionary."""
    try:
        return ComparisonResult(
            query=data["query"],
            verdict=data["verdict"],
            reasoning=data["reasoning"],
            internal_server_score=data.get("internal_server_score", 3),
            google_maps_score=data.get("google_maps_score", 3),
            model=data.get("model"),
            timestamp=data.get("timestamp")
        )
    except (KeyError, ValueError):
        return None
