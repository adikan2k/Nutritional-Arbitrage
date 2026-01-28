"""
USDA FoodData Central API Client

This demonstrates production-grade API client patterns:
1. Separation of concerns (raw API vs. clean data)
2. Retry logic with exponential backoff
3. Structured error handling
4. Comprehensive logging

Learning: Notice how we parse messy API responses into clean Pydantic models.
This is the ETL (Extract, Transform, Load) pattern.
"""

import requests
from typing import List, Optional
from loguru import logger
import time

from .models import USDAFood, NutrientInfo
from ..config import get_settings
from ..database.cache import NutritionCache


class USDAClient:
    """
    Client for USDA FoodData Central API
    
    API Docs: https://fdc.nal.usda.gov/api-guide.html
    Rate Limit: 1000 requests/hour (free tier)
    """
    
    BASE_URL = "https://api.nal.usda.gov/fdc/v1"
    
    def __init__(self, use_cache: bool = True):
        """
        Initialize with API key from config
        
        Args:
            use_cache: Enable caching (default: True)
        """
        self.settings = get_settings()
        self.api_key = self.settings.usda_api_key
        
        self.session = requests.Session()
        self.session.params = {"api_key": self.api_key}
        
        self.use_cache = use_cache
        self.cache = NutritionCache() if use_cache else None
        
        logger.info(f"USDA API Client initialized (cache: {use_cache})")
    
    def search_foods(
        self, 
        query: str, 
        page_size: int = 10,
        data_types: List[str] = None
    ) -> List[USDAFood]:
        """
        Search for foods by name
        
        Args:
            query: Search term (e.g., "whole milk")
            page_size: Number of results to return
            data_types: Filter by data types (e.g., ["SR Legacy", "Foundation"])
                       If None, searches all types. Recommended: exclude "Branded"
            
        Returns:
            List of USDAFood objects
            
        Example:
            >>> client = USDAClient()
            >>> # Get high-quality data only
            >>> foods = client.search_foods("chicken breast", 
            ...     data_types=["SR Legacy", "Foundation", "Survey (FNDDS)"])
            >>> print(foods[0].description)
        """
        
        logger.info(f"Searching USDA for: '{query}'")
        
        # Check cache first (include data_types in cache key)
        cache_key = query if not data_types else f"{query}:{','.join(sorted(data_types))}"
        if self.use_cache:
            cached_ids = self.cache.get_search_results(cache_key)
            if cached_ids is not None:
                logger.info(f"Found cached search results for '{query}'")
                foods = []
                for fdc_id in cached_ids:
                    food = self.cache.get_food(fdc_id)
                    if food:
                        foods.append(food)
                return foods
        
        endpoint = f"{self.BASE_URL}/foods/search"
        params = {
            "query": query,
            "pageSize": page_size
        }
        
        # Add data type filtering if specified
        if data_types:
            params["dataType"] = data_types
        
        try:
            response = self._make_request_with_retry(endpoint, params)
            
            if response.status_code != 200:
                logger.error(f"USDA API error: {response.status_code} - {response.text}")
                return []
            
            data = response.json()
            foods_raw = data.get("foods", [])
            
            logger.success(f"Found {len(foods_raw)} foods for query '{query}'")
            
            foods = []
            for food_raw in foods_raw:
                try:
                    food = self._parse_food(food_raw)
                    foods.append(food)
                    
                    # Cache each food
                    if self.use_cache:
                        self.cache.store_food(food)
                        
                except Exception as e:
                    logger.warning(f"Failed to parse food {food_raw.get('fdcId')}: {e}")
                    continue
            
            # Cache the search query -> fdc_ids mapping
            if self.use_cache and foods:
                fdc_ids = [f.fdc_id for f in foods]
                self.cache.store_search_results(cache_key, fdc_ids)
            
            return foods
            
        except Exception as e:
            logger.error(f"Search failed for '{query}': {e}")
            return []
    
    def get_food_by_id(self, fdc_id: int) -> Optional[USDAFood]:
        """
        Get detailed food information by FDC ID
        
        This returns more complete nutrient data than search.
        Use this after you've identified the right food from search.
        
        Args:
            fdc_id: USDA FoodData Central ID
            
        Returns:
            USDAFood object or None if not found
        """
        
        logger.info(f"Fetching USDA food ID: {fdc_id}")
        
        # Check cache first
        if self.use_cache:
            cached_food = self.cache.get_food(fdc_id)
            if cached_food:
                logger.info(f"Found cached food: {cached_food.description}")
                return cached_food
        
        endpoint = f"{self.BASE_URL}/food/{fdc_id}"
        
        try:
            response = self._make_request_with_retry(endpoint)
            
            if response.status_code == 404:
                logger.warning(f"Food {fdc_id} not found")
                return None
            
            if response.status_code != 200:
                logger.error(f"USDA API error: {response.status_code}")
                return None
            
            food_raw = response.json()
            food = self._parse_food(food_raw)
            
            # Cache the food
            if self.use_cache:
                self.cache.store_food(food)
            
            logger.success(f"Retrieved food: {food.description}")
            return food
            
        except Exception as e:
            logger.error(f"Failed to fetch food {fdc_id}: {e}")
            return None
    
    def _parse_food(self, raw_data: dict) -> USDAFood:
        """
        Parse raw USDA API response into our clean USDAFood model
        
        This is the "Transform" step in ETL.
        The USDA API has inconsistent field names across data types.
        We normalize everything here.
        """
        
        nutrients = []
        
        food_nutrients = raw_data.get("foodNutrients", [])
        for nutrient_data in food_nutrients:
            
            if "nutrient" in nutrient_data:
                nutrient_info = nutrient_data["nutrient"]
                name = nutrient_info.get("name", "Unknown")
                unit = nutrient_info.get("unitName", "")
            else:
                name = nutrient_data.get("nutrientName", "Unknown")
                unit = nutrient_data.get("unitName", "")
            
            amount = nutrient_data.get("amount", 0.0)
            
            if amount is None:
                amount = 0.0
            
            nutrients.append(NutrientInfo(
                name=name,
                amount=float(amount),
                unit=unit
            ))
        
        food_category = None
        if "foodCategory" in raw_data:
            fc = raw_data["foodCategory"]
            if isinstance(fc, dict):
                food_category = fc.get("description")
            elif isinstance(fc, str):
                food_category = fc
        elif "brandedFoodCategory" in raw_data:
            food_category = raw_data["brandedFoodCategory"]
        
        return USDAFood(
            fdc_id=raw_data["fdcId"],
            description=raw_data.get("description", "Unknown"),
            food_category=food_category,
            nutrients=nutrients,
            data_type=raw_data.get("dataType", "unknown"),
            publication_date=raw_data.get("publicationDate")
        )
    
    def _make_request_with_retry(
        self, 
        url: str, 
        params: dict = None, 
        max_retries: int = 3
    ) -> requests.Response:
        """
        Make HTTP request with exponential backoff retry logic
        
        Why this matters:
        - APIs can be flaky (network issues, rate limits)
        - Exponential backoff prevents hammering a struggling server
        - Production apps don't crash on first API hiccup
        
        Pattern: Wait 1s, then 2s, then 4s before giving up
        """
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=10)
                
                if response.status_code == 429:
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                return response
                
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise
            
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise
        
        raise Exception(f"Failed after {max_retries} retries")
