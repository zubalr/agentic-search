"""
API Client for handling external API interactions.
Supports Solr API with retry logic and provides data structures for queries.
"""

import time
import logging
import csv
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class APIQuery:
    """Represents a query with keyword and optional location."""
    keyword: str
    lat: Optional[float] = None # Changed to float for consistency with script usage
    lng: Optional[float] = None # Changed to float for consistency with script usage

@dataclass
class APIResponse:
    """Represents an API response."""
    query: APIQuery
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    success: bool = False

class APIClient:
    """Generic API client with retry logic and configuration."""
    
    def __init__(self, 
                 base_url: str,
                 max_retries: int = 3,
                 timeout: int = 30,
                 backoff_factor: int = 2):
        self.base_url = base_url
        self.max_retries = max_retries
        self.timeout = timeout
        self.backoff_factor = backoff_factor
    
    def fetch_with_retries(self, params: Dict[str, Any]) -> Tuple[Optional[Dict], Optional[str]]:
        """Fetch data with exponential backoff retry logic."""
        delay = 2
        
        for attempt in range(1, self.max_retries + 1):
            try:
                import requests # Import here to avoid top-level dependency if not always needed
                response = requests.get(self.base_url, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response.json(), None
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{self.max_retries} failed: {str(e)}")
                if attempt == self.max_retries:
                    return None, str(e)
                time.sleep(delay)
                delay *= self.backoff_factor
        
        return None, "All retry attempts failed"


class SolrAPIClient(APIClient):
    """Specialized client for Solr API interactions."""
    
    def __init__(self, base_url: Optional[str] = None, **kwargs): # Made base_url optional
        # Default base URL can be overridden by config or direct argument
        default_url = "http://172.16.201.69:8086/solr/getGisDataUsingFuzzySearch"
        super().__init__(base_url or default_url, **kwargs)
    
    def search(self, query: APIQuery) -> APIResponse:
        """Search using Solr API with keyword and optional location."""
        params = {
            "searchKeyWord": query.keyword,
            "inputLanguage": 1
        }
        
        if query.lat is not None and query.lng is not None: # Check for None explicitly
            params.update({
                "originLat": str(query.lat), # Ensure lat/lng are strings for API
                "originLng": str(query.lng)
            })
        
        result, error = self.fetch_with_retries(params)
        
        return APIResponse(
            query=query,
            result=result,
            error=error,
            success=result is not None
        )
    
    def batch_search(self, queries: List[APIQuery]) -> List[APIResponse]:
        """Perform batch search for multiple queries."""
        responses = []
        total = len(queries)
        
        if total == 0:
            logger.info("No queries to process for Solr batch search.")
            return []

        logger.info(f"Starting batch search for {total} queries...")
        
        for i, query in enumerate(queries, 1):
            response = self.search(query)
            responses.append(response)
            
            if i % 50 == 0 or i == total:
                logger.info(f"Processed {i}/{total} queries")
        
        return responses


def load_queries_from_csv(file_path: str) -> List[APIQuery]:
    """Load queries from CSV file with keyword, lat, lng columns."""
    queries = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            # Skip header row
            try:
                header = next(reader, None)
                # Basic check for header, adjust if CSV format varies significantly
                if header and header[0].lower().strip() == "keyword":
                    pass # Header skipped
                else: # No header or non-standard header, rewind if first row was data
                    if header:
                        queries.append(_parse_csv_row_to_query(header))
            except StopIteration:
                logger.warning(f"CSV file {file_path} is empty.")
                return []

            for row in reader:
                queries.append(_parse_csv_row_to_query(row))
    except FileNotFoundError:
        logger.error(f"Keywords file not found: {file_path}")
    except Exception as e:
        logger.error(f"Error loading queries from {file_path}: {e}")
    
    return queries

def _parse_csv_row_to_query(row: List[str]) -> Optional[APIQuery]:
    """Helper to parse a single CSV row to an APIQuery object."""
    if not row or not row[0].strip():
        return None # Skip empty rows or rows with no keyword

    keyword = row[0].strip()
    lat, lng = None, None

    if len(row) >= 3 and row[1].strip() and row[2].strip():
        try:
            lat = float(row[1].strip())
            lng = float(row[2].strip())
        except ValueError:
            logger.warning(f"Could not parse lat/lng for keyword '{keyword}': {row[1]}, {row[2]}. Proceeding without location.")
            lat, lng = None, None
    
    return APIQuery(keyword=keyword, lat=lat, lng=lng)
