"""
Pydantic Data Models - The Schema Layer

Why Pydantic?
1. Runtime type checking (catches bad API data)
2. Automatic parsing (dict -> object)
3. Clear error messages when data is invalid
4. Self-documenting code

Industry Pattern: Define your data contracts upfront.
If the API returns unexpected data, you catch it immediately
instead of crashing later in your optimization logic.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class NutrientInfo(BaseModel):
    """
    Represents a single nutrient (e.g., Protein, Vitamin C)
    
    USDA API returns nutrients in a complex nested structure.
    This flattens it into something useful.
    """
    name: str = Field(..., description="Nutrient name (e.g., 'Protein')")
    amount: float = Field(..., description="Amount per 100g")
    unit: str = Field(..., description="Unit (e.g., 'g', 'mg')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Protein",
                "amount": 3.3,
                "unit": "g"
            }
        }


class USDAFood(BaseModel):
    """
    Represents a food item from USDA FoodData Central
    
    This is what our app works with internally.
    The raw API response is messier - we clean it here.
    """
    fdc_id: int = Field(..., description="USDA Food Data Central ID")
    description: str = Field(..., description="Food name/description")
    food_category: Optional[str] = Field(None, description="Category (e.g., 'Dairy')")
    
    nutrients: List[NutrientInfo] = Field(default_factory=list, description="Nutrient breakdown")
    
    data_type: str = Field(..., description="USDA data type (Foundation, SR Legacy, etc.)")
    
    publication_date: Optional[str] = Field(None, description="When data was published")
    
    class Config:
        json_schema_extra = {
            "example": {
                "fdc_id": 173410,
                "description": "Milk, whole, 3.25% milkfat",
                "food_category": "Dairy and Egg Products",
                "nutrients": [
                    {"name": "Protein", "amount": 3.3, "unit": "g"},
                    {"name": "Energy", "amount": 61, "unit": "kcal"}
                ],
                "data_type": "sr_legacy_food"
            }
        }
    
    def get_nutrient(self, nutrient_name: str) -> Optional[float]:
        """
        Helper to extract a specific nutrient value
        
        Example:
            protein = food.get_nutrient("Protein")
        """
        for nutrient in self.nutrients:
            if nutrient.name.lower() == nutrient_name.lower():
                return nutrient.amount
        return None


class KrogerProduct(BaseModel):
    """
    Represents a product from Kroger API
    
    We'll build this client next, but defining the model now
    shows good planning.
    """
    product_id: str = Field(..., description="Kroger product ID")
    upc: str = Field(..., description="Universal Product Code")
    description: str = Field(..., description="Product name")
    brand: Optional[str] = Field(None, description="Brand name")
    
    price: float = Field(..., description="Current price in dollars")
    size: Optional[str] = Field(None, description="Package size (e.g., '1 gal')")
    
    aisle_locations: List[str] = Field(default_factory=list, description="Store aisle locations")
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "0001111041700",
                "upc": "0001111041700",
                "description": "Kroger Whole Milk",
                "brand": "Kroger",
                "price": 3.99,
                "size": "1 gal"
            }
        }
