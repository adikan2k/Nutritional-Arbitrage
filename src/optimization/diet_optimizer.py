"""
Diet Optimizer - Linear Programming with PuLP

The Mathematical Brain of the Project

This solves the classic "Diet Problem":
Minimize: Total cost
Subject to: Meeting nutritional requirements

Industry Pattern: Operations Research
Linear programming is used in supply chain, logistics, finance, etc.
This shows you understand mathematical optimization - a rare skill.
"""

from pulp import LpMinimize, LpProblem, LpStatus, LpVariable, lpSum, value
from typing import List, Dict, Optional, Tuple
from loguru import logger

from ..ingestion.models import USDAFood, KrogerProduct


class DietOptimizer:
    """
    Optimize food selection to minimize cost while meeting nutrition goals
    
    Mathematical Formulation:
    
    Decision Variables:
        x_i = quantity (in grams) of food i to purchase
    
    Objective Function:
        minimize: Σ(price_i * x_i / serving_size_i)
    
    Constraints:
        Σ(nutrient_j_i * x_i) >= min_nutrient_j  (for each nutrient j)
        Σ(nutrient_j_i * x_i) <= max_nutrient_j  (optional upper bounds)
        x_i >= 0  (non-negativity)
        x_i <= max_quantity_i  (optional max per food)
    
    This is a Linear Program (LP) - solvable in polynomial time!
    """
    
    def __init__(self, problem_name: str = "Nutritional Arbitrage"):
        """
        Initialize optimizer
        
        Args:
            problem_name: Name for the optimization problem
        """
        self.problem_name = problem_name
        logger.info(f"Diet optimizer initialized: {problem_name}")
    
    def optimize(
        self,
        foods: Dict[str, USDAFood],
        prices: Dict[str, float],
        nutrition_targets: Dict[str, Tuple[float, float]],
        max_quantity_per_food: float = 1000.0,  # Max grams per food
        time_limit: int = 60  # Solver time limit in seconds
    ) -> Optional[Dict]:
        """
        Optimize food selection to meet nutrition goals at minimum cost
        
        Args:
            foods: Dict mapping food_key -> USDAFood object
            prices: Dict mapping food_key -> price in dollars
            nutrition_targets: Dict mapping nutrient_name -> (min, max) grams
                              e.g., {"Protein": (100, 150), "Carbs": (200, 300)}
            max_quantity_per_food: Maximum grams of any single food (prevents absurd solutions)
            time_limit: Maximum solver time
            
        Returns:
            Dict with optimization results or None if infeasible
            
        Example:
            >>> optimizer = DietOptimizer()
            >>> foods = {"chicken": usda_chicken, "rice": usda_rice}
            >>> prices = {"chicken": 5.99, "rice": 2.49}
            >>> targets = {"Protein": (100, 200), "Energy": (2000, 2500)}
            >>> result = optimizer.optimize(foods, prices, targets)
            >>> print(f"Optimal cost: ${result['total_cost']:.2f}")
        """
        
        logger.info(
            f"Starting optimization: {len(foods)} foods, "
            f"{len(nutrition_targets)} nutrition targets"
        )
        
        # Create optimization problem
        prob = LpProblem(self.problem_name, LpMinimize)
        
        # Decision variables: quantity of each food in grams
        food_vars = {}
        for food_key in foods.keys():
            food_vars[food_key] = LpVariable(
                f"food_{food_key}",
                lowBound=0,
                upBound=max_quantity_per_food,
                cat='Continuous'
            )
        
        # Objective function: minimize total cost
        # Price is per package, need to scale to per 100g
        # Assume prices are for ~1 lb (453.6g) packages for now
        cost_per_100g = {
            food_key: price / 4.536  # Convert $/lb to $/100g
            for food_key, price in prices.items()
        }
        
        prob += lpSum([
            cost_per_100g[food_key] * food_vars[food_key] / 100.0
            for food_key in foods.keys()
            if food_key in prices
        ]), "Total_Cost"
        
        # Nutritional constraints
        for nutrient_name, (min_amount, max_amount) in nutrition_targets.items():
            # Sum of nutrient from all foods must meet requirements
            nutrient_sum = lpSum([
                (foods[food_key].get_nutrient(nutrient_name) or 0) * food_vars[food_key] / 100.0
                for food_key in foods.keys()
            ])
            
            # Minimum constraint
            if min_amount is not None:
                prob += nutrient_sum >= min_amount, f"Min_{nutrient_name}"
            
            # Maximum constraint
            if max_amount is not None:
                prob += nutrient_sum <= max_amount, f"Max_{nutrient_name}"
        
        logger.info("Solving optimization problem...")
        
        # Solve
        prob.solve()
        
        # Check status
        status = LpStatus[prob.status]
        logger.info(f"Optimization status: {status}")
        
        if status != 'Optimal':
            logger.warning(f"No optimal solution found: {status}")
            return None
        
        # Extract results
        solution = {}
        total_cost = value(prob.objective)
        
        selected_foods = {}
        total_nutrients = {}
        
        for food_key, var in food_vars.items():
            quantity = value(var)
            
            if quantity > 0.1:  # Only include foods with meaningful quantities
                selected_foods[food_key] = {
                    "quantity_grams": quantity,
                    "food": foods[food_key],
                    "price": prices.get(food_key, 0) * (quantity / 453.6)  # Scale price
                }
                
                # Calculate nutrient contributions
                for nutrient_name in nutrition_targets.keys():
                    nutrient_value = foods[food_key].get_nutrient(nutrient_name)
                    if nutrient_value:
                        contribution = nutrient_value * quantity / 100.0
                        total_nutrients[nutrient_name] = total_nutrients.get(nutrient_name, 0) + contribution
        
        result = {
            "status": status,
            "total_cost": total_cost,
            "selected_foods": selected_foods,
            "total_nutrients": total_nutrients,
            "targets": nutrition_targets,
            "num_foods": len(selected_foods)
        }
        
        logger.success(
            f"Optimization complete! Cost: ${total_cost:.2f}, "
            f"Foods: {len(selected_foods)}"
        )
        
        return result
    
    def print_solution(self, result: Dict):
        """
        Pretty-print optimization results
        
        Args:
            result: Dict from optimize() method
        """
        
        if not result:
            print("No solution found")
            return
        
        print("\n" + "="*70)
        print("OPTIMIZATION RESULTS")
        print("="*70)
        
        print(f"\n💰 Total Cost: ${result['total_cost']:.2f}")
        print(f"📦 Foods Selected: {result['num_foods']}")
        
        print(f"\n🛒 Shopping List:")
        print("-" * 70)
        
        for food_key, data in result['selected_foods'].items():
            food = data['food']
            quantity = data['quantity_grams']
            price = data['price']
            
            print(f"\n{food.description}")
            print(f"   Quantity: {quantity:.0f}g ({quantity/453.6:.2f} lbs)")
            print(f"   Cost: ${price:.2f}")
        
        print(f"\n📊 Nutritional Profile:")
        print("-" * 70)
        
        for nutrient_name, total in result['total_nutrients'].items():
            min_target, max_target = result['targets'][nutrient_name]
            
            status = "✅"
            if min_target and total < min_target:
                status = "❌"
            elif max_target and total > max_target:
                status = "⚠️"
            
            print(f"{status} {nutrient_name:20} {total:>8.1f} ", end="")
            
            if min_target and max_target:
                print(f"(target: {min_target:.0f}-{max_target:.0f})")
            elif min_target:
                print(f"(min: {min_target:.0f})")
            else:
                print()


class SimpleDietOptimizer(DietOptimizer):
    """
    Simplified optimizer with common nutrition targets
    
    Makes it easy to optimize without specifying all constraints manually.
    """
    
    def optimize_for_macros(
        self,
        foods: Dict[str, USDAFood],
        prices: Dict[str, float],
        target_calories: float = 2000,
        target_protein_g: float = 150,
        target_carbs_g: float = 200,
        target_fat_g: float = 65,
        tolerance: float = 0.1  # 10% tolerance
    ) -> Optional[Dict]:
        """
        Optimize for common macro targets (calories, protein, carbs, fat)
        
        Args:
            foods: Available foods
            prices: Food prices
            target_calories: Daily calorie target
            target_protein_g: Daily protein in grams
            target_carbs_g: Daily carbs in grams  
            target_fat_g: Daily fat in grams
            tolerance: How flexible targets are (0.1 = ±10%)
            
        Returns:
            Optimization results
        """
        
        # Build nutrition targets with tolerance
        nutrition_targets = {
            "Energy": (
                target_calories * (1 - tolerance),
                target_calories * (1 + tolerance)
            ),
            "Protein": (
                target_protein_g * (1 - tolerance),
                target_protein_g * (1 + tolerance)
            ),
            "Carbohydrate, by difference": (
                target_carbs_g * (1 - tolerance),
                target_carbs_g * (1 + tolerance)
            ),
            "Total lipid (fat)": (
                target_fat_g * (1 - tolerance),
                target_fat_g * (1 + tolerance)
            )
        }
        
        return self.optimize(foods, prices, nutrition_targets)
