"""
Core modules for the agentic search system.
"""

from .api_client import APIQuery, APIResponse, SolrAPIClient
from .evaluation import evaluate_holistic_set

__all__ = [
    "APIQuery",
    "APIResponse", 
    "SolrAPIClient",
    #"evaluate_single_pair",
    "evaluate_holistic_set"
]
