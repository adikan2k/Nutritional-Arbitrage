"""
Curated Quality Foods Database

This module contains vetted FDC IDs from USDA's SR Legacy and Foundation databases.
All foods here have complete nutrient profiles (50-135 nutrients).

Industry Pattern: Curated Data Sources
Instead of searching unreliable APIs, maintain a vetted list of quality data.
This ensures consistency, performance, and data quality.
"""

from typing import Dict, List, Optional
from loguru import logger

from .usda_client import USDAClient
from .models import USDAFood


# Curated FDC IDs - All from SR Legacy/Foundation with complete data
QUALITY_FOOD_DATABASE = {
    "proteins": {
        "chicken_breast_cooked": {
            "fdc_id": 171477,
            "name": "Chicken breast, cooked, roasted",
            "nutrients": 98,
            "description": "Boneless, skinless chicken breast"
        },
        "salmon_raw": {
            "fdc_id": 175167,
            "name": "Salmon, Atlantic, wild, raw",
            "nutrients": 95,
            "description": "Wild Atlantic salmon"
        },
        "eggs_hard_boiled": {
            "fdc_id": 173424,
            "name": "Eggs, hard-boiled",
            "nutrients": 95,
            "description": "Whole egg, cooked"
        },
        "ground_beef_cooked": {
            "fdc_id": 174032,
            "name": "Beef, ground, 85% lean, cooked",
            "nutrients": 90,
            "description": "Ground beef, pan-broiled"
        },
        "turkey_breast": {
            "fdc_id": 171484,
            "name": "Turkey, breast, meat only, cooked, roasted",
            "nutrients": 85,
            "description": "Turkey breast without skin"
        },
        "tuna_canned": {
            "fdc_id": 175149,
            "name": "Fish, tuna, light, canned in water, drained",
            "nutrients": 80,
            "description": "Canned tuna in water"
        },
    },
    
    "vegetables": {
        "broccoli": {
            "fdc_id": 170379,
            "name": "Broccoli, raw",
            "nutrients": 122,
            "description": "Fresh broccoli"
        },
        "spinach": {
            "fdc_id": 168462,
            "name": "Spinach, raw",
            "nutrients": 115,
            "description": "Fresh spinach leaves"
        },
        "carrots": {
            "fdc_id": 170417,
            "name": "Carrots, raw",
            "nutrients": 100,
            "description": "Fresh carrots"
        },
        "bell_pepper_red": {
            "fdc_id": 170108,
            "name": "Peppers, sweet, red, raw",
            "nutrients": 105,
            "description": "Red bell peppers"
        },
        "tomatoes": {
            "fdc_id": 170457,
            "name": "Tomatoes, red, ripe, raw",
            "nutrients": 100,
            "description": "Fresh tomatoes"
        },
    },
    
    "grains": {
        "brown_rice_cooked": {
            "fdc_id": 168880,
            "name": "Rice, brown, long-grain, cooked",
            "nutrients": 95,
            "description": "Cooked brown rice"
        },
        "oats_dry": {
            "fdc_id": 173904,
            "name": "Cereals, oats, regular, not fortified, dry",
            "nutrients": 110,
            "description": "Rolled oats, uncooked"
        },
        "quinoa_cooked": {
            "fdc_id": 168917,
            "name": "Quinoa, cooked",
            "nutrients": 90,
            "description": "Cooked quinoa"
        },
        "whole_wheat_bread": {
            "fdc_id": 172687,
            "name": "Bread, whole-wheat, commercially prepared",
            "nutrients": 85,
            "description": "Whole wheat bread"
        },
    },
    
    "nuts_seeds": {
        "almonds": {
            "fdc_id": 170567,
            "name": "Nuts, almonds",
            "nutrients": 135,
            "description": "Raw almonds"
        },
        "walnuts": {
            "fdc_id": 170187,
            "name": "Nuts, walnuts, English",
            "nutrients": 125,
            "description": "English walnuts"
        },
        "peanut_butter": {
            "fdc_id": 172470,
            "name": "Peanut butter, smooth style",
            "nutrients": 100,
            "description": "Smooth peanut butter"
        },
        "chia_seeds": {
            "fdc_id": 170554,
            "name": "Seeds, chia seeds, dried",
            "nutrients": 95,
            "description": "Dried chia seeds"
        },
    },
    
    "dairy": {
        "milk_whole": {
            "fdc_id": 171265,
            "name": "Milk, whole, 3.25% milkfat",
            "nutrients": 120,
            "description": "Whole milk"
        },
        "yogurt_plain": {
            "fdc_id": 170903,
            "name": "Yogurt, plain, whole milk",
            "nutrients": 110,
            "description": "Plain whole milk yogurt"
        },
        "cheddar_cheese": {
            "fdc_id": 173419,
            "name": "Cheese, cheddar",
            "nutrients": 105,
            "description": "Cheddar cheese"
        },
        "greek_yogurt": {
            "fdc_id": 170895,
            "name": "Yogurt, Greek, plain, nonfat",
            "nutrients": 95,
            "description": "Nonfat Greek yogurt"
        },
    },
    
    "fruits": {
        "banana": {
            "fdc_id": 173944,
            "name": "Bananas, raw",
            "nutrients": 105,
            "description": "Fresh bananas"
        },
        "apple": {
            "fdc_id": 171688,
            "name": "Apples, raw, with skin",
            "nutrients": 110,
            "description": "Fresh apples"
        },
        "strawberries": {
            "fdc_id": 167762,
            "name": "Strawberries, raw",
            "nutrients": 100,
            "description": "Fresh strawberries"
        },
        "blueberries": {
            "fdc_id": 171711,
            "name": "Blueberries, raw",
            "nutrients": 105,
            "description": "Fresh blueberries"
        },
    },
    
    "legumes": {
        "black_beans_cooked": {
            "fdc_id": 173735,
            "name": "Beans, black, mature seeds, cooked, boiled",
            "nutrients": 90,
            "description": "Cooked black beans"
        },
        "lentils_cooked": {
            "fdc_id": 172421,
            "name": "Lentils, mature seeds, cooked, boiled",
            "nutrients": 95,
            "description": "Cooked lentils"
        },
        "chickpeas_cooked": {
            "fdc_id": 173757,
            "name": "Chickpeas, mature seeds, cooked, boiled",
            "nutrients": 90,
            "description": "Cooked chickpeas/garbanzo beans"
        },
    }
}


class QualityFoodDatabase:
    """
    Manager for curated quality foods
    
    This ensures your optimizer only works with complete, validated data.
    """
    
    def __init__(self, client: Optional[USDAClient] = None):
        """
        Initialize with USDA client
        
        Args:
            client: USDAClient instance (creates new if None)
        """
        self.client = client or USDAClient(use_cache=True)
        self._cache = {}  # In-memory cache of loaded foods
    
    def get_food(self, category: str, food_key: str) -> Optional[USDAFood]:
        """
        Get a specific food by category and key
        
        Args:
            category: Food category (e.g., "proteins", "vegetables")
            food_key: Food key (e.g., "chicken_breast_cooked")
            
        Returns:
            USDAFood object with complete nutrient data
            
        Example:
            >>> db = QualityFoodDatabase()
            >>> chicken = db.get_food("proteins", "chicken_breast_cooked")
            >>> print(f"Protein: {chicken.get_nutrient('Protein')}g")
        """
        
        cache_key = f"{category}:{food_key}"
        
        # Check memory cache first
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Get FDC ID from database
        if category not in QUALITY_FOOD_DATABASE:
            logger.error(f"Category '{category}' not found")
            return None
        
        if food_key not in QUALITY_FOOD_DATABASE[category]:
            logger.error(f"Food '{food_key}' not found in category '{category}'")
            return None
        
        food_info = QUALITY_FOOD_DATABASE[category][food_key]
        fdc_id = food_info["fdc_id"]
        
        # Fetch from USDA (uses SQLite cache automatically)
        food = self.client.get_food_by_id(fdc_id)
        
        if food:
            self._cache[cache_key] = food
            logger.info(f"Loaded {food_info['name']}")
        
        return food
    
    def get_category(self, category: str) -> Dict[str, USDAFood]:
        """
        Get all foods in a category
        
        Args:
            category: Category name (e.g., "proteins")
            
        Returns:
            Dict mapping food_key -> USDAFood
            
        Example:
            >>> db = QualityFoodDatabase()
            >>> proteins = db.get_category("proteins")
            >>> for key, food in proteins.items():
            >>>     print(f"{key}: {food.description}")
        """
        
        if category not in QUALITY_FOOD_DATABASE:
            logger.error(f"Category '{category}' not found")
            return {}
        
        foods = {}
        for food_key in QUALITY_FOOD_DATABASE[category].keys():
            food = self.get_food(category, food_key)
            if food:
                foods[food_key] = food
        
        logger.info(f"Loaded {len(foods)} foods from category '{category}'")
        return foods
    
    def get_all_foods(self) -> Dict[str, Dict[str, USDAFood]]:
        """
        Load all foods from database
        
        Returns:
            Nested dict: category -> food_key -> USDAFood
            
        Example:
            >>> db = QualityFoodDatabase()
            >>> all_foods = db.get_all_foods()
            >>> print(f"Total categories: {len(all_foods)}")
        """
        
        all_foods = {}
        
        for category in QUALITY_FOOD_DATABASE.keys():
            all_foods[category] = self.get_category(category)
        
        total_foods = sum(len(foods) for foods in all_foods.values())
        logger.info(f"Loaded {total_foods} foods from {len(all_foods)} categories")
        
        return all_foods
    
    def list_categories(self) -> List[str]:
        """Get list of available categories"""
        return list(QUALITY_FOOD_DATABASE.keys())
    
    def list_foods_in_category(self, category: str) -> List[Dict]:
        """
        List foods in a category with metadata
        
        Returns:
            List of dicts with food info (without fetching full data)
        """
        
        if category not in QUALITY_FOOD_DATABASE:
            return []
        
        return [
            {
                "key": key,
                "fdc_id": info["fdc_id"],
                "name": info["name"],
                "description": info["description"],
                "nutrients": info["nutrients"]
            }
            for key, info in QUALITY_FOOD_DATABASE[category].items()
        ]
    
    def get_food_info(self, category: str, food_key: str) -> Optional[Dict]:
        """Get metadata without fetching from API"""
        
        if category not in QUALITY_FOOD_DATABASE:
            return None
        
        if food_key not in QUALITY_FOOD_DATABASE[category]:
            return None
        
        info = QUALITY_FOOD_DATABASE[category][food_key].copy()
        info["key"] = food_key
        info["category"] = category
        
        return info
