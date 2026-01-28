"""
SQLite Caching Layer - Performance Optimization

Why Cache?
- USDA API: 1000 requests/hour limit
- Latency: 500ms per API call vs 2ms from SQLite
- Cost: Free tier has limits, cache is unlimited

Pattern: "Read-Through Cache"
1. Check cache first
2. If miss, fetch from API
3. Store in cache for next time

This is how production systems scale without hitting rate limits.
"""

import sqlite3
import json
from typing import Optional, List
from pathlib import Path
from datetime import datetime
from loguru import logger

from ..ingestion.models import USDAFood, NutrientInfo
from ..config import get_settings


class NutritionCache:
    """
    SQLite-based cache for USDA nutrition data
    
    Schema:
    - usda_foods: Stores complete food records
    - search_cache: Stores search query results
    
    Why SQLite?
    - Zero setup (file-based)
    - Fast for reads (perfect for caching)
    - Embedded (no separate server)
    - ACID compliant (safe concurrent access)
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize cache and create tables if needed
        
        Args:
            db_path: Path to SQLite database file (defaults to config)
        """
        if db_path is None:
            settings = get_settings()
            db_path = settings.database_path
        
        # Ensure parent directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        
        self._create_tables()
        logger.info(f"Cache initialized at: {db_path}")
    
    def _create_tables(self):
        """
        Create cache tables if they don't exist
        
        Design Decisions:
        - fdc_id is primary key (unique identifier)
        - Store complete food as JSON (flexible schema)
        - Add created_at for cache invalidation later
        - Add index on description for fast text search
        """
        
        cursor = self.conn.cursor()
        
        # Table 1: Store complete USDA food records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usda_foods (
                fdc_id INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                food_category TEXT,
                data_type TEXT,
                nutrients_json TEXT NOT NULL,
                publication_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Index for faster lookups by description
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_description 
            ON usda_foods(description)
        """)
        
        # Table 2: Cache search results (query -> list of fdc_ids)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_cache (
                query TEXT PRIMARY KEY,
                fdc_ids_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.commit()
        logger.debug("Cache tables created/verified")
    
    def get_food(self, fdc_id: int) -> Optional[USDAFood]:
        """
        Retrieve a food from cache by FDC ID
        
        Returns:
            USDAFood object if cached, None if cache miss
        """
        
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM usda_foods WHERE fdc_id = ?",
            (fdc_id,)
        )
        
        row = cursor.fetchone()
        
        if row is None:
            logger.debug(f"Cache MISS: Food {fdc_id}")
            return None
        
        logger.debug(f"Cache HIT: Food {fdc_id}")
        
        # Reconstruct USDAFood from cached data
        nutrients_data = json.loads(row["nutrients_json"])
        nutrients = [NutrientInfo(**n) for n in nutrients_data]
        
        return USDAFood(
            fdc_id=row["fdc_id"],
            description=row["description"],
            food_category=row["food_category"],
            nutrients=nutrients,
            data_type=row["data_type"],
            publication_date=row["publication_date"]
        )
    
    def store_food(self, food: USDAFood):
        """
        Store a food in the cache
        
        Uses INSERT OR REPLACE to handle duplicates gracefully.
        This is called after fetching from USDA API.
        """
        
        cursor = self.conn.cursor()
        
        # Serialize nutrients to JSON
        nutrients_json = json.dumps([
            {"name": n.name, "amount": n.amount, "unit": n.unit}
            for n in food.nutrients
        ])
        
        cursor.execute("""
            INSERT OR REPLACE INTO usda_foods 
            (fdc_id, description, food_category, data_type, nutrients_json, publication_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            food.fdc_id,
            food.description,
            food.food_category,
            food.data_type,
            nutrients_json,
            food.publication_date
        ))
        
        self.conn.commit()
        logger.debug(f"Cached food: {food.description} (FDC {food.fdc_id})")
    
    def get_search_results(self, query: str) -> Optional[List[int]]:
        """
        Get cached search results for a query
        
        Returns:
            List of FDC IDs if cached, None if cache miss
        """
        
        # Normalize query (lowercase, strip whitespace)
        query_normalized = query.lower().strip()
        
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT fdc_ids_json FROM search_cache WHERE query = ?",
            (query_normalized,)
        )
        
        row = cursor.fetchone()
        
        if row is None:
            logger.debug(f"Cache MISS: Search '{query}'")
            return None
        
        logger.debug(f"Cache HIT: Search '{query}'")
        return json.loads(row["fdc_ids_json"])
    
    def store_search_results(self, query: str, fdc_ids: List[int]):
        """
        Cache search results
        
        Stores the query and list of FDC IDs that were returned.
        """
        
        query_normalized = query.lower().strip()
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO search_cache (query, fdc_ids_json)
            VALUES (?, ?)
        """, (query_normalized, json.dumps(fdc_ids)))
        
        self.conn.commit()
        logger.debug(f"Cached search: '{query}' -> {len(fdc_ids)} results")
    
    def get_cache_stats(self) -> dict:
        """
        Get cache statistics for monitoring
        
        Useful for understanding cache hit rates and performance.
        """
        
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM usda_foods")
        foods_count = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(*) as count FROM search_cache")
        searches_count = cursor.fetchone()["count"]
        
        # Get database file size
        db_size_bytes = Path(self.db_path).stat().st_size
        db_size_mb = db_size_bytes / (1024 * 1024)
        
        return {
            "foods_cached": foods_count,
            "searches_cached": searches_count,
            "db_size_mb": round(db_size_mb, 2)
        }
    
    def clear_cache(self):
        """
        Clear all cached data
        
        Useful for testing or if you want fresh data from API.
        """
        
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM usda_foods")
        cursor.execute("DELETE FROM search_cache")
        self.conn.commit()
        
        logger.warning("Cache cleared!")
    
    def close(self):
        """Close database connection"""
        self.conn.close()
        logger.debug("Cache connection closed")
