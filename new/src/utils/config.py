"""
Configuration management for the agentic search system.
Handles environment variables, file paths, and model configurations.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class Config:
    """Main configuration class for the agentic search system."""
    
    # File paths
    data_dir: str = "data"
    raw_dir: str = "raw"
    output_dir: str = "output"
    
    # Input files
    analytics_file: str = "data/Analytics.json"
    keywords_csv: str = "data/representative_keywords_with_location.csv"
    
    # Result files
    internal_results_file: str = "raw/api_results_solr.jsonl"
    google_results_file: str = "raw/google_places_results.jsonl"
    comparison_memory_file: str = "output/comparison_memory.jsonl"
    failed_queries_file: str = "output/failed_queries.txt"
    
    # API Configuration
    solr_api_url: str = "http://172.16.201.69:8086/solr/getGisDataUsingFuzzySearch"
    google_places_api_url: str = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    
    # API Keys (loaded from environment)
    cerebras_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    google_places_api_key: Optional[str] = None
    
    # Processing settings
    batch_size: int = 5
    delay_between_batches: float = 10.0
    delay_between_queries: float = 2.0
    max_retries: int = 3
    timeout: int = 30
    
    # Default location (Karachi)
    default_lat: str = "24.8607"
    default_lng: str = "67.0011"
    
    # LLM model configurations
    llm_models: List[Dict[str, Any]] = field(default_factory=lambda: [
        {"provider": "cerebras", "model_name": "llama-3.3-70b"},
        {"provider": "groq", "model_name": "llama-3.3-70b-versatile"}
    ])
    
    # Evaluation settings
    evaluation_threshold: float = 0.7
    deepeval_model: str = "cerebras/llama-3.3-70b"
    
    def __post_init__(self):
        """Load environment variables and validate configuration."""
        self._load_env_vars()
        self._validate_paths()
        self._ensure_directories()
    
    def _load_env_vars(self):
        """Load configuration from environment variables."""
        # API Keys
        self.cerebras_api_key = os.getenv("CEREBRAS_API_KEY")
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.google_places_api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        
        # File paths
        self.internal_results_file = os.getenv("INTERNAL_RESULTS_FILE", self.internal_results_file)
        self.google_results_file = os.getenv("GOOGLE_RESULTS_FILE", self.google_results_file)
        self.comparison_memory_file = os.getenv("COMPARISON_MEMORY_FILE", self.comparison_memory_file)
        self.failed_queries_file = os.getenv("FAILED_QUERIES_FILE", self.failed_queries_file)
        
        # Processing settings
        self.batch_size = int(os.getenv("BATCH_SIZE", self.batch_size))
        self.delay_between_batches = float(os.getenv("DELAY_BETWEEN_BATCHES", self.delay_between_batches))
        
        # API URLs
        self.solr_api_url = os.getenv("SOLR_API_URL", self.solr_api_url)
        self.google_places_api_url = os.getenv("GOOGLE_PLACES_API_URL", self.google_places_api_url)
    
    def _validate_paths(self):
        """Validate that critical files exist."""
        if not os.path.exists(self.analytics_file):
            logger.warning(f"Analytics file not found: {self.analytics_file}")
    
    def _ensure_directories(self):
        """Ensure that necessary directories exist."""
        directories = [self.data_dir, self.raw_dir, self.output_dir]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def get_file_path(self, file_type: str) -> str:
        """Get absolute path for a file type."""
        file_map = {
            "analytics": self.analytics_file,
            "keywords_csv": self.keywords_csv,
            "internal_results": self.internal_results_file,
            "google_results": self.google_results_file,
            "comparison_memory": self.comparison_memory_file,
            "failed_queries": self.failed_queries_file
        }
        
        if file_type not in file_map:
            raise ValueError(f"Unknown file type: {file_type}")
        
        return os.path.abspath(file_map[file_type])
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration dictionary."""
        return {
            "solr": {
                "url": self.solr_api_url,
                "max_retries": self.max_retries,
                "timeout": self.timeout
            },
            "google_places": {
                "url": self.google_places_api_url,
                "api_key": self.google_places_api_key,
                "max_retries": self.max_retries,
                "timeout": self.timeout
            }
        }
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration dictionary."""
        return {
            "models": self.llm_models,
            "api_keys": {
                "cerebras": self.cerebras_api_key,
                "groq": self.groq_api_key
            },
            "batch_size": self.batch_size,
            "delay_between_batches": self.delay_between_batches
        }
    
    def update_from_dict(self, config_dict: Dict[str, Any]):
        """Update configuration from a dictionary."""
        for key, value in config_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logger.info(f"Updated config: {key} = {value}")
    
    def save_to_file(self, file_path: str):
        """Save configuration to a JSON file."""
        config_dict = {
            "data_dir": self.data_dir,
            "raw_dir": self.raw_dir,
            "output_dir": self.output_dir,
            "batch_size": self.batch_size,
            "delay_between_batches": self.delay_between_batches,
            "llm_models": self.llm_models,
            "evaluation_threshold": self.evaluation_threshold,
            "deepeval_model": self.deepeval_model
        }
        
        with open(file_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        logger.info(f"Configuration saved to {file_path}")
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'Config':
        """Load configuration from a JSON file."""
        with open(file_path, 'r') as f:
            config_dict = json.load(f)
        
        config = cls()
        config.update_from_dict(config_dict)
        return config


# Global configuration instance
_config: Optional[Config] = None

def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config

def set_config(config: Config):
    """Set the global configuration instance."""
    global _config
    _config = config

def load_config_from_file(file_path: str) -> Config:
    """Load configuration from file and set as global config."""
    config = Config.load_from_file(file_path)
    set_config(config)
    return config

def reset_config():
    """Reset the global configuration to default."""
    global _config
    _config = Config()
    return _config
