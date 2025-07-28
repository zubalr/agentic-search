"""
Data processing utilities for keyword extraction, sorting, and deduplication.
"""

import csv
import json
import logging
from typing import List, Dict, Set, Tuple, Any
from collections import Counter
from pathlib import Path

logger = logging.getLogger(__name__)

class DataProcessor:
    """Handles data processing operations for keywords and search results."""
    
    @staticmethod
    def extract_keywords_from_analytics(analytics_file: str) -> List[str]:
        """Extract keywords from Analytics.json file."""
        keywords = []
        
        try:
            with open(analytics_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
                
                # Extract keywords from the analytics data structure
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'keyword' in item:
                            keywords.append(item['keyword'])
                elif isinstance(data, dict):
                    # Handle different analytics data structures
                    for key, value in data.items():
                        if 'keyword' in str(key).lower():
                            if isinstance(value, str):
                                keywords.append(value)
                            elif isinstance(value, list):
                                keywords.extend(value)
                
        except Exception as e:
            logger.error(f"Error extracting keywords from {analytics_file}: {e}")
        
        return keywords
    
    @staticmethod
    def sort_keywords(keywords: List[str]) -> List[str]:
        """Sort keywords alphabetically and remove empty entries."""
        # Filter out empty or whitespace-only keywords
        cleaned_keywords = [kw.strip() for kw in keywords if kw.strip()]
        return sorted(cleaned_keywords)
    
    @staticmethod
    def remove_duplicates(keywords: List[str]) -> List[str]:
        """Remove duplicate keywords while preserving order."""
        seen = set()
        unique_keywords = []
        
        for keyword in keywords:
            keyword_lower = keyword.lower().strip()
            if keyword_lower not in seen:
                seen.add(keyword_lower)
                unique_keywords.append(keyword.strip())
        
        return unique_keywords
    
    @staticmethod
    def select_representative_keywords(keywords: List[str], 
                                     max_count: int = 500,
                                     min_frequency: int = 1) -> List[str]:
        """Select representative keywords based on frequency and importance."""
        # Count keyword frequencies
        keyword_counts = Counter(kw.lower().strip() for kw in keywords)
        
        # Filter by minimum frequency
        filtered_keywords = [
            kw for kw, count in keyword_counts.items() 
            if count >= min_frequency
        ]
        
        # Sort by frequency (descending) and then alphabetically
        sorted_keywords = sorted(
            filtered_keywords,
            key=lambda x: (-keyword_counts[x], x)
        )
        
        # Take top keywords up to max_count
        return sorted_keywords[:max_count]
    
    @staticmethod
    def add_location_to_keywords(keywords: List[str], 
                               default_lat: str = "24.8607", 
                               default_lng: str = "67.0011") -> List[Tuple[str, str, str]]:
        """Add default location (Karachi) to keywords."""
        return [(keyword, default_lat, default_lng) for keyword in keywords]
    
    @staticmethod
    def save_keywords_to_txt(keywords: List[str], output_file: str):
        """Save keywords to a text file, one per line."""
        try:
            with open(output_file, 'w', encoding='utf-8') as file:
                for keyword in keywords:
                    file.write(f"{keyword}\n")
            logger.info(f"Saved {len(keywords)} keywords to {output_file}")
        except Exception as e:
            logger.error(f"Error saving keywords to {output_file}: {e}")
    
    @staticmethod
    def save_keywords_with_location_to_csv(keywords_with_location: List[Tuple[str, str, str]], 
                                         output_file: str):
        """Save keywords with location to CSV file."""
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['keyword', 'lat', 'lng'])  # Header
                for keyword, lat, lng in keywords_with_location:
                    writer.writerow([keyword, lat, lng])
            logger.info(f"Saved {len(keywords_with_location)} keywords with location to {output_file}")
        except Exception as e:
            logger.error(f"Error saving keywords with location to {output_file}: {e}")
    
    @staticmethod
    def load_keywords_from_txt(input_file: str) -> List[str]:
        """Load keywords from a text file."""
        keywords = []
        try:
            with open(input_file, 'r', encoding='utf-8') as file:
                keywords = [line.strip() for line in file if line.strip()]
            logger.info(f"Loaded {len(keywords)} keywords from {input_file}")
        except Exception as e:
            logger.error(f"Error loading keywords from {input_file}: {e}")
        return keywords
    
    @staticmethod
    def load_keywords_from_csv(input_file: str) -> List[Tuple[str, str, str]]:
        """Load keywords with location from CSV file."""
        keywords_with_location = []
        try:
            with open(input_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                next(reader, None)  # Skip header if present
                for row in reader:
                    if len(row) >= 3:
                        keyword, lat, lng = row[0].strip(), row[1].strip(), row[2].strip()
                        if keyword and lat and lng:
                            keywords_with_location.append((keyword, lat, lng))
            logger.info(f"Loaded {len(keywords_with_location)} keywords with location from {input_file}")
        except Exception as e:
            logger.error(f"Error loading keywords from {input_file}: {e}")
        return keywords_with_location
    
    @staticmethod
    def process_pipeline(analytics_file: str, 
                        output_dir: str,
                        max_keywords: int = 500,
                        add_location: bool = True,
                        default_lat: str = "24.8607",
                        default_lng: str = "67.0011") -> Dict[str, str]:
        """
        Complete processing pipeline for keywords.
        
        Returns dict with paths to generated files.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Extract keywords
        logger.info("Extracting keywords from analytics data...")
        keywords = DataProcessor.extract_keywords_from_analytics(analytics_file)
        
        # Step 2: Sort keywords
        logger.info("Sorting keywords...")
        sorted_keywords = DataProcessor.sort_keywords(keywords)
        
        # Step 3: Remove duplicates
        logger.info("Removing duplicates...")
        unique_keywords = DataProcessor.remove_duplicates(sorted_keywords)
        
        # Step 4: Select representative keywords
        logger.info(f"Selecting representative keywords (max: {max_keywords})...")
        representative_keywords = DataProcessor.select_representative_keywords(
            unique_keywords, max_count=max_keywords
        )
        
        # Save results
        output_files = {}
        
        # Save sorted keywords
        sorted_file = output_path / "sorted_keywords.txt"
        DataProcessor.save_keywords_to_txt(sorted_keywords, str(sorted_file))
        output_files['sorted'] = str(sorted_file)
        
        # Save unique keywords
        unique_file = output_path / "unique_sorted_keywords.txt"
        DataProcessor.save_keywords_to_txt(unique_keywords, str(unique_file))
        output_files['unique'] = str(unique_file)
        
        # Save representative keywords
        representative_file = output_path / "representative_keywords.txt"
        DataProcessor.save_keywords_to_txt(representative_keywords, str(representative_file))
        output_files['representative'] = str(representative_file)
        
        if add_location:
            # Add location and save to CSV
            keywords_with_location = DataProcessor.add_location_to_keywords(
                representative_keywords, default_lat, default_lng
            )
            
            csv_file = output_path / "representative_keywords_with_location.csv"
            DataProcessor.save_keywords_with_location_to_csv(keywords_with_location, str(csv_file))
            output_files['representative_with_location'] = str(csv_file)
        
        logger.info(f"Processing pipeline completed. Generated files: {list(output_files.keys())}")
        return output_files
