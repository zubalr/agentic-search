"""
API Client for handling external API interactions.
Supports Solr and Google Places API with retry logic and rate limiting.
"""

import json
import time
import logging
import csv
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import requests
import google.maps.places as places_v1
from google.maps.places import SearchTextRequest, SearchNearbyRequest, GetPlaceRequest
from google.maps.places import Circle, Place

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
    """Specialized client for Google Places API interactions using the official client library."""

    def __init__(self, api_key: str, **kwargs):
        super().__init__("https://places.googleapis.com", **kwargs)
        self.api_key = api_key
        # Initialize the Places client
        from google.api_core.client_options import ClientOptions
        import os
        os.environ['GOOGLE_API_KEY'] = api_key
        self.client = places_v1.PlacesClient(
            client_options=ClientOptions(api_key=api_key)
        )
        # Default field mask for comprehensive data
        self.default_field_mask = "places.id,places.displayName,places.formattedAddress,places.location,places.types,places.websiteUri,places.internationalPhoneNumber,places.rating,places.userRatingCount,places.priceLevel,places.businessStatus,places.currentOpeningHours,places.photos,places.reviews"

    def search_text(self, query: APIQuery, field_mask: Optional[str] = None) -> APIResponse:
        """Text Search using Google Places API v1 with official client library."""
        try:
            # Build the request
            request = SearchTextRequest()
            request.text_query = query.keyword
            
            # Add location bias if available
            if query.lat and query.lng:
                try:
                    lat = float(query.lat)
                    lng = float(query.lng)
                    if lat != 0.0 or lng != 0.0:
                        location_bias = places_v1.SearchTextRequest.LocationBias()
                        circle = Circle()
                        circle.center.latitude = lat
                        circle.center.longitude = lng
                        circle.radius = 5000.0  # 5km radius
                        location_bias.circle = circle
                        request.location_bias = location_bias
                except (ValueError, TypeError):
                    pass
            
            # Make the request with field mask header - always use "*" to get all fields
            response = self.client.search_text(
                request=request,
                metadata=[("x-goog-fieldmask", "*")]
            )
            
            # Convert to dict format for compatibility
            result = {
                "places": [self._place_to_dict(place) for place in response.places]
            }
            
            return APIResponse(
                query=query,
                result=result,
                error=None,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Text search failed for query {query.keyword}: {str(e)}")
            return APIResponse(
                query=query,
                result=None,
                error=str(e),
                success=False
            )

    def search_nearby(self, query: APIQuery, field_mask: Optional[str] = None) -> APIResponse:
        """Nearby Search using Google Places API v1 with official client library."""
        if not (query.lat and query.lng):
            return APIResponse(
                query=query,
                result=None,
                error="lat/lng required for nearby search",
                success=False
            )
        
        try:
            lat = float(query.lat)
            lng = float(query.lng)
        except (ValueError, TypeError):
            return APIResponse(
                query=query,
                result=None,
                error="Invalid lat/lng values",
                success=False
            )
        
        try:
            # Build the request
            request = SearchNearbyRequest()
            
            # Set location restriction (required for nearby search)
            location_restriction = places_v1.SearchNearbyRequest.LocationRestriction()
            circle = Circle()
            circle.center.latitude = lat
            circle.center.longitude = lng
            circle.radius = 5000.0  # 5km radius
            location_restriction.circle = circle
            request.location_restriction = location_restriction
            
            # Note: SearchNearbyRequest doesn't support keyword field
            # We rely on location-based search only
            
            # Make the request with field mask header - always use "*" to get all fields
            response = self.client.search_nearby(
                request=request,
                metadata=[("x-goog-fieldmask", "*")]
            )
            
            # Convert to dict format for compatibility
            result = {
                "places": [self._place_to_dict(place) for place in response.places]
            }
            
            return APIResponse(
                query=query,
                result=result,
                error=None,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Nearby search failed for query {query.keyword}: {str(e)}")
            return APIResponse(
                query=query,
                result=None,
                error=str(e),
                success=False
            )

    def get_place_details(self, place_id: str, field_mask: Optional[str] = None) -> Tuple[Optional[Dict], Optional[str]]:
        """Get Place Details using Google Places API v1 with official client library."""
        try:
            # Build the request
            request = GetPlaceRequest()
            request.name = f"places/{place_id}"
            
            # Make the request with field mask header - always use "*" to get all fields
            place = self.client.get_place(
                request=request,
                metadata=[("x-goog-fieldmask", "*")]
            )
            
            # Convert to dict format
            result = self._place_to_dict(place)
            
            return result, None
            
        except Exception as e:
            logger.error(f"Get place details failed for place_id {place_id}: {str(e)}")
            return None, str(e)

    def _place_to_dict(self, place: Place) -> Dict[str, Any]:
        """Convert a Place object to a dictionary for compatibility."""
        result = {}
        
        try:
            # Basic information
            if hasattr(place, 'id') and place.id:
                result['id'] = place.id
            if hasattr(place, 'display_name') and place.display_name:
                result['displayName'] = {'text': place.display_name.text}
            if hasattr(place, 'formatted_address') and place.formatted_address:
                result['formattedAddress'] = place.formatted_address
            
            # Location
            if hasattr(place, 'location') and place.location:
                result['location'] = {
                    'latitude': place.location.latitude,
                    'longitude': place.location.longitude
                }
            
            # Types
            if hasattr(place, 'types') and place.types:
                result['types'] = list(place.types)
            
            # Contact information
            if hasattr(place, 'website_uri') and place.website_uri:
                result['websiteUri'] = place.website_uri
            if hasattr(place, 'international_phone_number') and place.international_phone_number:
                result['internationalPhoneNumber'] = place.international_phone_number
            
            # Ratings
            if hasattr(place, 'rating') and place.rating:
                result['rating'] = place.rating
            if hasattr(place, 'user_rating_count') and place.user_rating_count:
                result['userRatingCount'] = place.user_rating_count
            
            # Price level
            if hasattr(place, 'price_level') and place.price_level:
                result['priceLevel'] = place.price_level.name
            
            # Business status
            if hasattr(place, 'business_status') and place.business_status:
                result['businessStatus'] = place.business_status.name
            
            # Opening hours
            if hasattr(place, 'current_opening_hours') and place.current_opening_hours:
                opening_hours = {}
                if hasattr(place.current_opening_hours, 'open_now'):
                    opening_hours['open_now'] = place.current_opening_hours.open_now
                if hasattr(place.current_opening_hours, 'weekday_text') and place.current_opening_hours.weekday_text:
                    opening_hours['weekday_text'] = list(place.current_opening_hours.weekday_text)
                if opening_hours:
                    result['currentOpeningHours'] = opening_hours
            
            # Photos
            if hasattr(place, 'photos') and place.photos:
                result['photos'] = [
                    {
                        'name': photo.name,
                        'width_px': photo.width_px,
                        'height_px': photo.height_px
                    }
                    for photo in place.photos[:5]  # Limit to first 5 photos
                ]
            
            # Reviews
            if hasattr(place, 'reviews') and place.reviews:
                result['reviews'] = [
                    {
                        'author_name': review.author_attribution.display_name if review.author_attribution else 'Anonymous',
                        'rating': review.rating,
                        'text': review.text.text if review.text else '',
                        'time': review.publish_time.seconds if review.publish_time else None
                    }
                    for review in place.reviews[:5]  # Limit to first 5 reviews
                ]
        
        except Exception as e:
            logger.warning(f"Error converting place to dict: {str(e)}")
            # Return at least the basic info we could extract
            pass
        
        return result


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
