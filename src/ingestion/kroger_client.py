"""
Kroger API Client - Product Prices & Availability

Kroger API uses OAuth2 authentication - more complex than USDA.
This demonstrates production-grade API integration patterns.

API Docs: https://developer.kroger.com/reference
Rate Limit: 10,000 requests/day (free tier)

Industry Pattern: OAuth2 Client Credentials Flow
Most commercial APIs use OAuth2. This shows you know how to handle it.
"""

import requests
import time
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from loguru import logger

from .models import KrogerProduct
from ..config import get_settings


class KrogerClient:
    """
    Client for Kroger API with OAuth2 authentication
    
    Key Concepts:
    - OAuth2: Get access token first, then use for API calls
    - Token expires after 30 minutes - need to refresh
    - Location-based: Products vary by store
    """
    
    BASE_URL = "https://api.kroger.com/v1"
    AUTH_URL = "https://api.kroger.com/v1/connect/oauth2/token"
    
    def __init__(self):
        """Initialize with credentials from config"""
        self.settings = get_settings()
        self.client_id = self.settings.kroger_client_id
        self.client_secret = self.settings.kroger_client_secret
        self.location_id = self.settings.kroger_location_id
        
        self.session = requests.Session()
        
        # OAuth2 token management
        self._access_token = None
        self._token_expires_at = None
        
        # Get initial token
        self._refresh_token()
        
        logger.info("Kroger API Client initialized")
    
    def _refresh_token(self):
        """
        Get new OAuth2 access token
        
        OAuth2 Client Credentials Flow:
        1. POST client_id + client_secret
        2. Get access_token (expires in 30 min)
        3. Use token in Authorization header
        
        Industry Standard: Most commercial APIs use this
        """
        
        logger.debug("Refreshing Kroger OAuth2 token...")
        
        # Prepare authentication request
        auth_data = {
            "grant_type": "client_credentials",
            "scope": "product.compact"  # Scope for product search
        }
        
        try:
            response = requests.post(
                self.AUTH_URL,
                auth=(self.client_id, self.client_secret),
                data=auth_data,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                raise Exception(f"Failed to get Kroger access token: {response.status_code}")
            
            token_data = response.json()
            
            self._access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 1800)  # Default 30 min
            
            # Set expiration time (refresh 5 min early to be safe)
            self._token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
            
            # Update session with token
            self.session.headers.update({
                "Authorization": f"Bearer {self._access_token}",
                "Accept": "application/json"
            })
            
            logger.success(f"OAuth2 token refreshed (expires in {expires_in}s)")
            
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise
    
    def _ensure_valid_token(self):
        """Check if token is expired and refresh if needed"""
        
        if self._token_expires_at is None or datetime.now() >= self._token_expires_at:
            logger.info("Token expired, refreshing...")
            self._refresh_token()
    
    def search_products(
        self, 
        query: str, 
        limit: int = 10,
        location_id: str = None
    ) -> List[KrogerProduct]:
        """
        Search for products at Kroger
        
        Args:
            query: Product search term (e.g., "chicken breast")
            limit: Number of results (max 50)
            location_id: Store location ID (uses config default if None)
            
        Returns:
            List of KrogerProduct objects with prices
            
        Example:
            >>> client = KrogerClient()
            >>> products = client.search_products("chicken breast")
            >>> for p in products:
            >>>     print(f"{p.description}: ${p.price}")
        """
        
        self._ensure_valid_token()
        
        logger.info(f"Searching Kroger for: '{query}'")
        
        endpoint = f"{self.BASE_URL}/products"
        
        params = {
            "filter.term": query,
            "filter.locationId": location_id or self.location_id,
            "filter.limit": min(limit, 50)  # API max is 50
        }
        
        try:
            response = self._make_request_with_retry(endpoint, params)
            
            if response.status_code != 200:
                logger.error(f"Kroger API error: {response.status_code} - {response.text}")
                return []
            
            data = response.json()
            products_raw = data.get("data", [])
            
            logger.success(f"Found {len(products_raw)} products for '{query}'")
            
            # Parse into KrogerProduct objects
            products = []
            for product_raw in products_raw:
                try:
                    product = self._parse_product(product_raw)
                    products.append(product)
                except Exception as e:
                    logger.warning(f"Failed to parse product {product_raw.get('productId')}: {e}")
                    continue
            
            return products
            
        except Exception as e:
            logger.error(f"Search failed for '{query}': {e}")
            return []
    
    def get_product_by_id(self, product_id: str) -> Optional[KrogerProduct]:
        """
        Get detailed product info by Kroger product ID
        
        Args:
            product_id: Kroger product ID
            
        Returns:
            KrogerProduct object or None
        """
        
        self._ensure_valid_token()
        
        logger.info(f"Fetching Kroger product: {product_id}")
        
        endpoint = f"{self.BASE_URL}/products/{product_id}"
        params = {"filter.locationId": self.location_id}
        
        try:
            response = self._make_request_with_retry(endpoint, params)
            
            if response.status_code == 404:
                logger.warning(f"Product {product_id} not found")
                return None
            
            if response.status_code != 200:
                logger.error(f"Kroger API error: {response.status_code}")
                return None
            
            data = response.json()
            product_raw = data.get("data")
            
            if not product_raw:
                return None
            
            product = self._parse_product(product_raw)
            logger.success(f"Retrieved: {product.description}")
            
            return product
            
        except Exception as e:
            logger.error(f"Failed to fetch product {product_id}: {e}")
            return None
    
    def _parse_product(self, raw_data: dict) -> KrogerProduct:
        """
        Parse raw Kroger API response into KrogerProduct model
        
        Kroger's API structure is complex - this extracts the essentials.
        """
        
        # Extract basic info
        product_id = raw_data.get("productId", "")
        upc = raw_data.get("upc", "")
        description = raw_data.get("description", "Unknown")
        brand = raw_data.get("brand", "")
        
        # Extract price (nested in items array)
        price = 0.0
        size = None
        
        items = raw_data.get("items", [])
        if items:
            item = items[0]  # Use first item
            
            # Price
            price_data = item.get("price", {})
            regular_price = price_data.get("regular", 0.0)
            promo_price = price_data.get("promo", 0.0)
            
            # Use promo price if available, otherwise regular
            price = promo_price if promo_price > 0 else regular_price
            
            # Size
            size = item.get("size")
        
        # Aisle locations
        aisle_locations = []
        aisles = raw_data.get("aisleLocations", [])
        for aisle in aisles:
            description = aisle.get("description", "")
            if description:
                aisle_locations.append(description)
        
        return KrogerProduct(
            product_id=product_id,
            upc=upc,
            description=description,
            brand=brand,
            price=price,
            size=size,
            aisle_locations=aisle_locations
        )
    
    def _make_request_with_retry(
        self,
        url: str,
        params: dict = None,
        max_retries: int = 3
    ) -> requests.Response:
        """
        Make HTTP request with retry logic
        
        Same pattern as USDA client - production best practice
        """
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=10)
                
                # Handle rate limiting
                if response.status_code == 429:
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                # Token expired mid-request
                if response.status_code == 401:
                    logger.warning("Token expired, refreshing...")
                    self._refresh_token()
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
