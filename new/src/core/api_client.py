"""
API Client for handling external API interactions.
Supports Solr and Google Places API with retry logic and rate limiting.
"""

import json
import requests
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
    lat: Optional[str] = None
    lng: Optional[str] = None

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
    
    def __init__(self, base_url: str = "http://172.16.201.69:8086/solr/getGisDataUsingFuzzySearch", **kwargs):
        super().__init__(base_url, **kwargs)
    
    def search(self, query: APIQuery) -> APIResponse:
        """Search using Solr API with keyword and optional location."""
        params = {
            "searchKeyWord": query.keyword,
            "inputLanguage": 1
        }
        
        if query.lat and query.lng:
            params.update({
                "originLat": query.lat,
                "originLng": query.lng
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
        
        logger.info(f"Starting batch search for {total} queries...")
        
        for i, query in enumerate(queries, 1):
            response = self.search(query)
            responses.append(response)
            
            if i % 50 == 0 or i == total:
                logger.info(f"Processed {i}/{total} queries")
        
        return responses


class GooglePlacesAPIClient(APIClient):
    """Specialized client for Google Places API interactions."""
    

    def __init__(self, api_key: str, **kwargs):
        # Default base URLs for each endpoint
        self.text_search_url = "https://places.googleapis.com/v1/places:searchText"
        self.nearby_search_url = "https://places.googleapis.com/v1/places:searchNearby"
        self.place_details_url = "https://places.googleapis.com/v1/places/"
        super().__init__(self.text_search_url, **kwargs)
        self.api_key = api_key
        # Default field mask: display name and address
        self.field_mask = "places.displayName,places.formattedAddress"

    def search_text(self, query: APIQuery, field_mask: Optional[str] = None) -> APIResponse:
        """Text Search using Google Places API v1."""
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": field_mask or self.field_mask
        }
        body = {"textQuery": query.keyword}
        if query.lat and query.lng:
            try:
                lat = float(query.lat)
                lng = float(query.lng)
                if lat != 0.0 or lng != 0.0:
                    body["locationBias"] = {
                        "circle": {
                            "center": {"latitude": lat, "longitude": lng},
                            "radius": 5000.0
                        }
                    }
            except Exception:
                pass
        delay = 2
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(self.text_search_url, headers=headers, json=body, timeout=self.timeout)
                response.raise_for_status()
                result = response.json()
                return APIResponse(query=query, result=result, error=None, success=True)
            except Exception as e:
                logger.warning(f"Text Search attempt {attempt}/{self.max_retries} failed: {str(e)}")
                if attempt == self.max_retries:
                    return APIResponse(query=query, result=None, error=str(e), success=False)
                time.sleep(delay)
                delay *= self.backoff_factor

    def search_nearby(self, query: APIQuery, field_mask: Optional[str] = None) -> APIResponse:
        """Nearby Search using Google Places API v1."""
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": field_mask or self.field_mask
        }
        # Nearby search requires locationRestriction
        if not (query.lat and query.lng):
            return APIResponse(query=query, result=None, error="lat/lng required for nearby search", success=False)
        try:
            lat = float(query.lat)
            lng = float(query.lng)
        except Exception:
            return APIResponse(query=query, result=None, error="Invalid lat/lng", success=False)
        body = {
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": 5000.0
                }
            }
        }
        if query.keyword:
            body["keyword"] = query.keyword
        delay = 2
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(self.nearby_search_url, headers=headers, json=body, timeout=self.timeout)
                response.raise_for_status()
                result = response.json()
                return APIResponse(query=query, result=result, error=None, success=True)
            except Exception as e:
                logger.warning(f"Nearby Search attempt {attempt}/{self.max_retries} failed: {str(e)}")
                if attempt == self.max_retries:
                    return APIResponse(query=query, result=None, error=str(e), success=False)
                time.sleep(delay)
                delay *= self.backoff_factor

    def get_place_details(self, place_id: str, field_mask: Optional[str] = None) -> Tuple[Optional[Dict], Optional[str]]:
        """Get Place Details using Google Places API v1."""
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": field_mask or "*"
        }
        url = self.place_details_url + place_id
        delay = 2
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(url, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                return response.json(), None
            except Exception as e:
                logger.warning(f"Place Details attempt {attempt}/{self.max_retries} failed: {str(e)}")
                if attempt == self.max_retries:
                    return None, str(e)
                time.sleep(delay)
                delay *= self.backoff_factor


def load_queries_from_csv(file_path: str) -> List[APIQuery]:
    """Load queries from CSV file with keyword, lat, lng columns."""
    queries = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            # Skip header row
            next(reader, None)
            
            for row in reader:
                if len(row) >= 3:
                    keyword, lat, lng = row[0].strip(), row[1].strip(), row[2].strip()
                    if keyword and lat and lng and keyword != "keyword":  # Skip any remaining header-like rows
                        queries.append(APIQuery(keyword=keyword, lat=lat, lng=lng))
                elif len(row) >= 1:
                    keyword = row[0].strip()
                    if keyword and keyword != "keyword":
                        queries.append(APIQuery(keyword=keyword))
    except Exception as e:
        logger.error(f"Error loading queries from {file_path}: {e}")
    
    return queries


def save_responses_to_jsonl(responses: List[APIResponse], file_path: str, failed_file_path: str):
    """Save API responses to JSONL files (success and failures separately)."""
    successful_count = 0
    failed_count = 0
    
    with open(file_path, 'w') as success_file, open(failed_file_path, 'w') as failed_file:
        for response in responses:
            response_data = {
                "query": {
                    "keyword": response.query.keyword,
                    "lat": response.query.lat,
                    "lng": response.query.lng
                }
            }
            
            if response.success:
                response_data["result"] = response.result
                success_file.write(json.dumps(response_data) + "\n")
                successful_count += 1
            else:
                response_data["error"] = response.error
                failed_file.write(json.dumps(response_data) + "\n")
                failed_count += 1
    
    logger.info(f"Saved {successful_count} successful responses to {file_path}")
    logger.info(f"Saved {failed_count} failed responses to {failed_file_path}")
