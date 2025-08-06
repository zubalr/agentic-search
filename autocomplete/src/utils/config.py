"""
Configuration management for the autocomplete data fetching script.
Handles environment variables, file paths, and API-specific settings.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Config:
    """Configuration class for the autocomplete data fetching script."""
    
    # File paths
    data_dir: str = "data"
    raw_dir: str = "raw"
    
    # Input files
    keywords_csv: str = "data/representative_keywords_with_location.csv"
    
    # API Configuration
    solr_api_url: str = "http://172.16.201.69:8086/solr/getGisDataUsingFuzzySearch"
    
    # API Keys (loaded from environment)
    google_places_api_key: Optional[str] = None
    
    # Processing settings for Solr API client
    max_retries: int = 3
    timeout: int = 30
    
    # Default location (Doha, Qatar - matching script's hardcoded default)
    default_lat: float = 25.3246603
    default_lng: float = 51.4382779
    
    def __post_init__(self):
        """Load environment variables and validate configuration."""
        self._load_env_vars()
        self._ensure_directories()
    
    def _load_env_vars(self):
        """Load configuration from environment variables."""
        self.google_places_api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        self.solr_api_url = os.getenv("SOLR_API_URL", self.solr_api_url)
        
        # Allow overriding default lat/lng via environment if needed
        env_lat = os.getenv("DEFAULT_LAT")
        env_lng = os.getenv("DEFAULT_LNG")
        if env_lat:
            try:
                self.default_lat = float(env_lat)
            except ValueError:
                logger.warning(f"Invalid DEFAULT_LAT value: {env_lat}. Using default.")
        if env_lng:
            try:
                self.default_lng = float(env_lng)
            except ValueError:
                logger.warning(f"Invalid DEFAULT_LNG value: {env_lng}. Using default.")
    
    def _ensure_directories(self):
        """Ensure that necessary directories exist."""
        directories = [self.data_dir, self.raw_dir]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def get_solr_config(self) -> Dict[str, Any]:
        """Get Solr API configuration dictionary."""
        return {
            "url": self.solr_api_url,
            "max_retries": self.max_retries,
            "timeout": self.timeout
        }

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

def reset_config():
    """Reset the global configuration to default."""
    global _config
    _config = Config()
    return _config
