"""
Smart Food Search - Get Only Complete Nutrient Profiles

This module filters out incomplete data and returns only foods
with real nutrient information suitable for optimization.

Industry Pattern: Data Quality Filtering
Never pass garbage into your optimizer - filter at the ingestion layer.
"""

from typing import List, Optional
from loguru import logger

from .usda_client import USDAClient
from .models import USDAFood


class SmartFoodSearch:
    """
    Intelligent food search that filters for complete nutrient data
    
    Problem: USDA search returns mix of complete and incomplete data
    Solution: Filter for foods with real nutrient values
    """
    
    def __init__(self, client: Optional[USDAClient] = None):
        """
        Initialize with USDA client
        
        Args:
            client: USDAClient instance (creates new one if None)
        """
        self.client = client or USDAClient(use_cache=True)
    
    def search_complete_foods(
        self,
        query: str,
        min_nutrients: int = 5,
        page_size: int = 20
    ) -> List[USDAFood]:
        """
        Search for foods with COMPLETE nutrient profiles
        
        This is what you'll use in your optimizer!
        
        Args:
            query: Food to search for
            min_nutrients: Minimum non-zero nutrients required (default: 5)
            page_size: Number of results to fetch (searches more to find complete ones)
            
        Returns:
            List of foods with complete nutrient data
            
        Example:
            >>> searcher = SmartFoodSearch()
            >>> foods = searcher.search_complete_foods("chicken breast")
            >>> for food in foods:
            >>>     print(f"{food.description}: {food.get_nutrient('Protein')}g protein")
        """
        
        logger.info(f"Smart search for: '{query}' (requiring {min_nutrients}+ nutrients)")
        
        # Search USDA (get more results to filter from)
        all_foods = self.client.search_foods(query, page_size=page_size)
        
        if not all_foods:
            logger.warning(f"No results found for '{query}'")
            return []
        
        # Filter for complete data
        complete_foods = []
        
        for food in all_foods:
            completeness = self._assess_completeness(food)
            
            if completeness["non_zero_count"] >= min_nutrients:
                complete_foods.append(food)
                logger.debug(
                    f"✓ {food.description}: {completeness['non_zero_count']} nutrients, "
                    f"{completeness['completeness']:.0f}% complete"
                )
            else:
                logger.debug(
                    f"✗ {food.description}: Only {completeness['non_zero_count']} nutrients "
                    f"(need {min_nutrients})"
                )
        
        logger.info(
            f"Found {len(complete_foods)}/{len(all_foods)} foods with complete data"
        )
        
        return complete_foods
    
    def get_best_match(self, query: str) -> Optional[USDAFood]:
        """
        Get the single best food match with complete data
        
        Returns the first result with the most complete nutrient profile.
        
        Args:
            query: Food to search for
            
        Returns:
            Single best matching food, or None
        """
        
        foods = self.search_complete_foods(query, page_size=10)
        
        if not foods:
            return None
        
        # Sort by completeness
        foods_with_scores = [
            (food, self._assess_completeness(food)["non_zero_count"])
            for food in foods
        ]
        
        foods_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        best_food = foods_with_scores[0][0]
        logger.info(f"Best match: {best_food.description}")
        
        return best_food
    
    def _assess_completeness(self, food: USDAFood) -> dict:
        """
        Assess how complete a food's nutrient profile is
        
        Returns:
            Dict with completeness metrics
        """
        
        total_nutrients = len(food.nutrients)
        non_zero = sum(1 for n in food.nutrients if n.amount > 0)
        
        # Check for essential macros
        essential = {
            "Protein": food.get_nutrient("Protein"),
            "Energy": food.get_nutrient("Energy"),
            "Fat": food.get_nutrient("Total lipid (fat)"),
            "Carbs": food.get_nutrient("Carbohydrate, by difference")
        }
        
        has_essentials = sum(1 for v in essential.values() if v and v > 0)
        
        completeness = (non_zero / total_nutrients * 100) if total_nutrients > 0 else 0
        
        return {
            "total_nutrients": total_nutrients,
            "non_zero_count": non_zero,
            "has_essentials": has_essentials,
            "completeness": completeness,
            "is_complete": non_zero >= 5 and has_essentials >= 3
        }
    
    def search_by_category(
        self,
        category: str,
        queries: List[str],
        min_nutrients: int = 5
    ) -> dict:
        """
        Search multiple foods in a category
        
        Useful for building a shopping list by category.
        
        Args:
            category: Category name (e.g., "Proteins", "Vegetables")
            queries: List of food queries
            min_nutrients: Minimum non-zero nutrients required
            
        Returns:
            Dict mapping query -> list of complete foods
            
        Example:
            >>> searcher = SmartFoodSearch()
            >>> proteins = searcher.search_by_category(
            ...     "Proteins",
            ...     ["chicken breast", "salmon", "eggs", "tofu"]
            ... )
        """
        
        logger.info(f"Searching category '{category}' with {len(queries)} queries")
        
        results = {}
        
        for query in queries:
            foods = self.search_complete_foods(query, min_nutrients=min_nutrients, page_size=10)
            results[query] = foods
            
            if foods:
                logger.info(f"  ✓ {query}: {len(foods)} complete foods")
            else:
                logger.warning(f"  ✗ {query}: No complete foods found")
        
        return results
    
    def get_nutrition_summary(self, food: USDAFood) -> dict:
        """
        Get a clean summary of key nutrients
        
        Returns:
            Dict with main nutrients for display
        """
        
        return {
            "description": food.description,
            "fdc_id": food.fdc_id,
            "data_type": food.data_type,
            "category": food.food_category,
            "calories": food.get_nutrient("Energy"),
            "protein_g": food.get_nutrient("Protein"),
            "fat_g": food.get_nutrient("Total lipid (fat)"),
            "carbs_g": food.get_nutrient("Carbohydrate, by difference"),
            "fiber_g": food.get_nutrient("Fiber, total dietary"),
            "total_nutrients": len(food.nutrients),
            "non_zero_nutrients": sum(1 for n in food.nutrients if n.amount > 0)
        }


def print_food_summary(food: USDAFood):
    """Helper to print a nice summary of a food"""
    
    print(f"\n{'='*60}")
    print(f"📊 {food.description}")
    print(f"{'='*60}")
    print(f"FDC ID: {food.fdc_id}")
    print(f"Type: {food.data_type}")
    print(f"Category: {food.food_category}")
    print(f"\nPer 100g:")
    
    calories = food.get_nutrient("Energy")
    protein = food.get_nutrient("Protein")
    fat = food.get_nutrient("Total lipid (fat)")
    carbs = food.get_nutrient("Carbohydrate, by difference")
    fiber = food.get_nutrient("Fiber, total dietary")
    
    if calories:
        print(f"  Calories: {calories} kcal")
    if protein:
        print(f"  Protein: {protein}g")
    if fat:
        print(f"  Fat: {fat}g")
    if carbs:
        print(f"  Carbs: {carbs}g")
    if fiber:
        print(f"  Fiber: {fiber}g")
    
    non_zero = sum(1 for n in food.nutrients if n.amount > 0)
    print(f"\nTotal nutrients: {len(food.nutrients)} ({non_zero} with values)")
