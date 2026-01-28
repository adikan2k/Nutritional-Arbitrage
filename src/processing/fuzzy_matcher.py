"""
Fuzzy String Matcher - Link Kroger Products to USDA Foods

Problem: "Kroger Chicken Breast" needs to match "Chicken breast, cooked, roasted"
Solution: RapidFuzz for intelligent string similarity

Industry Pattern: Record Linkage
Matching records across different databases is a core data engineering skill.
This demonstrates you understand data quality and integration challenges.
"""

from rapidfuzz import fuzz, process
from typing import List, Optional, Dict, Tuple
from loguru import logger

from ..ingestion.models import KrogerProduct, USDAFood


class FoodMatcher:
    """
    Intelligent matcher to link Kroger products with USDA nutrition data
    
    Uses multiple matching strategies:
    1. Token Sort Ratio - Handles word order differences
    2. Partial Ratio - Handles extra brand/description text
    3. Category validation - Ensures logical matches
    
    Example Matches:
    "Simple Truth Organic Chicken Breast" → "Chicken breast, cooked, roasted"
    "Kroger Whole Milk 1 Gal" → "Milk, whole, 3.25% milkfat"
    """
    
    def __init__(self, min_score: int = 70):
        """
        Initialize matcher
        
        Args:
            min_score: Minimum similarity score (0-100) to consider a match
                      70 is a good default - strict enough to avoid bad matches
        """
        self.min_score = min_score
        logger.info(f"FoodMatcher initialized (min_score: {min_score})")
    
    def find_best_match(
        self,
        kroger_product: KrogerProduct,
        usda_foods: List[USDAFood],
        category_hint: Optional[str] = None
    ) -> Optional[Tuple[USDAFood, float]]:
        """
        Find the best USDA food match for a Kroger product
        
        Args:
            kroger_product: Product from Kroger
            usda_foods: List of USDA foods to match against
            category_hint: Optional category (e.g., "protein", "dairy") to improve matching
            
        Returns:
            Tuple of (matched_food, confidence_score) or None
            
        Example:
            >>> matcher = FoodMatcher()
            >>> kroger_product = ... # chicken breast from Kroger
            >>> usda_foods = ... # list of USDA foods
            >>> match, score = matcher.find_best_match(kroger_product, usda_foods)
            >>> print(f"Matched to {match.description} with {score}% confidence")
        """
        
        if not usda_foods:
            logger.warning("No USDA foods provided for matching")
            return None
        
        # Prepare search text from Kroger product
        search_text = self._prepare_search_text(kroger_product)
        
        logger.debug(f"Matching '{search_text}' against {len(usda_foods)} USDA foods")
        
        # Extract just the descriptions for matching
        food_descriptions = [food.description for food in usda_foods]
        
        # Use RapidFuzz to find best matches
        # token_sort_ratio: Handles word order ("chicken breast" vs "breast chicken")
        matches = process.extract(
            search_text,
            food_descriptions,
            scorer=fuzz.token_sort_ratio,
            limit=5  # Get top 5 candidates
        )
        
        if not matches:
            logger.warning(f"No matches found for '{search_text}'")
            return None
        
        # Find the best valid match
        for match_text, score, index in matches:
            if score >= self.min_score:
                matched_food = usda_foods[index]
                
                # Validate the match makes sense
                if self._validate_match(kroger_product, matched_food, category_hint):
                    logger.info(
                        f"Matched '{kroger_product.description}' → "
                        f"'{matched_food.description}' (score: {score})"
                    )
                    return (matched_food, score)
                else:
                    logger.debug(f"Match rejected: {match_text} (failed validation)")
        
        logger.warning(f"No valid matches above threshold for '{search_text}'")
        return None
    
    def match_multiple(
        self,
        kroger_products: List[KrogerProduct],
        usda_foods: List[USDAFood],
        category_hint: Optional[str] = None
    ) -> Dict[str, Tuple[USDAFood, float]]:
        """
        Match multiple Kroger products to USDA foods
        
        Args:
            kroger_products: List of Kroger products
            usda_foods: List of USDA foods
            category_hint: Optional category for all products
            
        Returns:
            Dict mapping kroger_product_id -> (usda_food, score)
        """
        
        matches = {}
        
        for kroger_product in kroger_products:
            match_result = self.find_best_match(kroger_product, usda_foods, category_hint)
            
            if match_result:
                matches[kroger_product.product_id] = match_result
        
        logger.info(f"Matched {len(matches)}/{len(kroger_products)} products")
        
        return matches
    
    def _prepare_search_text(self, kroger_product: KrogerProduct) -> str:
        """
        Prepare Kroger product text for matching
        
        Cleans up brand names, packaging info, etc.
        """
        
        # Start with description
        text = kroger_product.description.lower()
        
        # Remove common brand indicators
        brands_to_remove = [
            'kroger', 'simple truth', 'private selection',
            'heritage farm', 'organic', 'natural'
        ]
        
        for brand in brands_to_remove:
            text = text.replace(brand, '')
        
        # Remove common packaging terms
        packaging_terms = [
            'fresh', 'frozen', 'canned', 'pack', 'family size',
            'value pack', 'lb', 'oz', 'gal', 'ct'
        ]
        
        for term in packaging_terms:
            text = text.replace(term, '')
        
        # Clean up whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def _validate_match(
        self,
        kroger_product: KrogerProduct,
        usda_food: USDAFood,
        category_hint: Optional[str] = None
    ) -> bool:
        """
        Validate that a match makes logical sense
        
        This prevents bad matches like:
        - "Chicken breast" matching to "Chicken soup"
        - "Milk" matching to "Milk chocolate"
        
        Returns:
            True if match is valid, False otherwise
        """
        
        # If we have a category hint, check USDA food category
        if category_hint and usda_food.food_category:
            category_keywords = {
                'protein': ['meat', 'poultry', 'fish', 'seafood', 'egg'],
                'dairy': ['dairy', 'milk', 'cheese', 'yogurt'],
                'vegetables': ['vegetable'],
                'fruits': ['fruit'],
                'grains': ['cereal', 'grain', 'bread', 'pasta'],
                'nuts': ['nut', 'seed']
            }
            
            if category_hint.lower() in category_keywords:
                keywords = category_keywords[category_hint.lower()]
                category_lower = usda_food.food_category.lower()
                
                # Check if any keyword is in the category
                if not any(keyword in category_lower for keyword in keywords):
                    logger.debug(
                        f"Category mismatch: expected {category_hint}, "
                        f"got {usda_food.food_category}"
                    )
                    return False
        
        # Additional validation: Check for anti-patterns
        kroger_text = kroger_product.description.lower()
        usda_text = usda_food.description.lower()
        
        # Don't match processed versions to raw (or vice versa) unless it's close
        if 'raw' in usda_text and 'cooked' in kroger_text:
            return False
        
        if 'cooked' in usda_text and 'raw' in kroger_text:
            return False
        
        return True
    
    def get_match_details(
        self,
        kroger_product: KrogerProduct,
        usda_food: USDAFood
    ) -> Dict:
        """
        Get detailed matching information for debugging/display
        
        Returns:
            Dict with match details and scores
        """
        
        search_text = self._prepare_search_text(kroger_product)
        
        # Calculate different similarity scores
        token_sort = fuzz.token_sort_ratio(search_text, usda_food.description.lower())
        partial = fuzz.partial_ratio(search_text, usda_food.description.lower())
        simple = fuzz.ratio(search_text, usda_food.description.lower())
        
        return {
            "kroger_product": kroger_product.description,
            "kroger_cleaned": search_text,
            "usda_food": usda_food.description,
            "scores": {
                "token_sort_ratio": token_sort,
                "partial_ratio": partial,
                "simple_ratio": simple
            },
            "kroger_brand": kroger_product.brand,
            "usda_category": usda_food.food_category,
            "usda_data_type": usda_food.data_type
        }


class SmartFoodMatcher(FoodMatcher):
    """
    Enhanced matcher with category-aware matching
    
    This version automatically determines categories from product text
    and uses them to improve matching accuracy.
    """
    
    def __init__(self, min_score: int = 70):
        super().__init__(min_score)
        
        # Category detection keywords
        self.category_keywords = {
            'protein': ['chicken', 'beef', 'pork', 'turkey', 'fish', 'salmon', 
                       'tuna', 'egg', 'meat', 'steak'],
            'dairy': ['milk', 'cheese', 'yogurt', 'cream', 'butter'],
            'vegetables': ['broccoli', 'carrot', 'spinach', 'lettuce', 'tomato',
                          'pepper', 'onion', 'celery', 'cucumber'],
            'fruits': ['apple', 'banana', 'orange', 'berry', 'grape', 'melon'],
            'grains': ['rice', 'bread', 'pasta', 'oat', 'quinoa', 'cereal'],
            'nuts': ['almond', 'walnut', 'peanut', 'cashew', 'pecan']
        }
    
    def detect_category(self, text: str) -> Optional[str]:
        """
        Auto-detect category from product text
        
        Args:
            text: Product description
            
        Returns:
            Detected category or None
        """
        
        text_lower = text.lower()
        
        for category, keywords in self.category_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return category
        
        return None
    
    def find_best_match(
        self,
        kroger_product: KrogerProduct,
        usda_foods: List[USDAFood],
        category_hint: Optional[str] = None
    ) -> Optional[Tuple[USDAFood, float]]:
        """
        Enhanced matching with auto-category detection
        """
        
        # Auto-detect category if not provided
        if not category_hint:
            category_hint = self.detect_category(kroger_product.description)
            if category_hint:
                logger.debug(f"Auto-detected category: {category_hint}")
        
        # Use parent class matching with category
        return super().find_best_match(kroger_product, usda_foods, category_hint)
