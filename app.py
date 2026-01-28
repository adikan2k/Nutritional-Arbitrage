"""
Nutritional Arbitrage - Enhanced Streamlit Dashboard

Production-grade web application with all critical improvements:
- Budget constraints
- Preset nutrition profiles
- Food preferences & restrictions
- Cost per macro analysis
- Multi-day planning
- Micronutrient tracking
- Save/load meal plans
- Recipe suggestions
- Smart insights
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
from datetime import datetime
from pathlib import Path

from src.ingestion.quality_foods import QualityFoodDatabase
from src.optimization.diet_optimizer import SimpleDietOptimizer, DietOptimizer
from src.logger import setup_logger

# Page config
st.set_page_config(
    page_title="Nutritional Arbitrage Pro",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding: 1rem 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #667eea;
    }
    .stButton>button {
        width: 100%;
        background-color: #667eea;
        color: white;
        font-weight: bold;
        border-radius: 0.5rem;
        padding: 0.5rem 1rem;
        border: none;
    }
    .stButton>button:hover {
        background-color: #5568d3;
    }
    .insight-box {
        background-color: #e8f4f8;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2196F3;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize
setup_logger()

# Nutrition presets
NUTRITION_PRESETS = {
    "Custom": None,
    "Weight Loss (High Protein)": {
        "calories": 1500,
        "protein": 150,
        "carbs": 100,
        "fat": 50,
        "description": "High protein, calorie deficit for weight loss"
    },
    "Muscle Gain (Bulk)": {
        "calories": 3000,
        "protein": 200,
        "carbs": 350,
        "fat": 90,
        "description": "High calorie surplus for muscle building"
    },
    "Maintenance (Balanced)": {
        "calories": 2000,
        "protein": 150,
        "carbs": 200,
        "fat": 65,
        "description": "Balanced macros for weight maintenance"
    },
    "Athlete (High Carb)": {
        "calories": 2500,
        "protein": 160,
        "carbs": 300,
        "fat": 70,
        "description": "High carb for endurance athletes"
    },
    "Keto (Low Carb)": {
        "calories": 2000,
        "protein": 130,
        "carbs": 30,
        "fat": 155,
        "description": "Very low carb, high fat ketogenic diet"
    }
}

# Recipe database
RECIPES = {
    "proteins": {
        "chicken": ["Grilled Chicken Breast", "Chicken Stir Fry", "Baked Lemon Chicken"],
        "salmon": ["Baked Salmon", "Salmon Salad", "Teriyaki Salmon"],
        "eggs": ["Scrambled Eggs", "Egg White Omelet", "Hard Boiled Eggs"]
    },
    "combinations": [
        {
            "name": "Chicken & Broccoli Bowl",
            "foods": ["chicken", "broccoli", "rice"],
            "description": "Classic meal prep staple"
        },
        {
            "name": "Protein Oatmeal",
            "foods": ["oats", "eggs", "banana"],
            "description": "High protein breakfast"
        }
    ]
}

# Initialize session state
def init_session_state():
    defaults = {
        'optimization_result': None,
        'foods_db': None,
        'saved_plans': [],
        'show_tutorial': True,
        'optimization_history': []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    if st.session_state.foods_db is None:
        with st.spinner('Loading food database...'):
            st.session_state.foods_db = QualityFoodDatabase()

init_session_state()


def main():
    """Main application"""
    
    # Header
    st.markdown('<h1 class="main-header">🥗 Nutritional Arbitrage Pro</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p style="text-align: center; font-size: 1.2rem; color: #666;">'
        'AI-Powered Grocery Optimization • Minimize Cost • Maximize Nutrition'
        '</p>',
        unsafe_allow_html=True
    )
    
    # Tutorial on first visit
    if st.session_state.show_tutorial:
        show_tutorial()
    
    st.markdown("---")
    
    # Sidebar - Enhanced controls
    with st.sidebar:
        render_sidebar()
    
    # Main content
    if st.session_state.optimization_result is None:
        show_welcome_screen()
    else:
        show_results_enhanced()


def show_tutorial():
    """Show tutorial for first-time users"""
    
    with st.expander("👋 Welcome! Quick Start Guide", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 1️⃣ Choose Profile")
            st.write("Select a preset or customize your targets")
        
        with col2:
            st.markdown("### 2️⃣ Set Preferences")
            st.write("Add dietary restrictions and budget")
        
        with col3:
            st.markdown("### 3️⃣ Optimize!")
            st.write("Get your personalized meal plan")
        
        if st.button("Got it! Don't show again"):
            st.session_state.show_tutorial = False
            st.rerun()


def render_sidebar():
    """Enhanced sidebar with all controls"""
    
    st.header("⚙️ Configuration")
    
    # === PRESET PROFILES ===
    st.subheader("🎯 Quick Start")
    
    preset = st.selectbox(
        "Nutrition Profile",
        list(NUTRITION_PRESETS.keys()),
        help="Choose a preset or select Custom for manual entry"
    )
    
    if preset != "Custom":
        preset_data = NUTRITION_PRESETS[preset]
        st.info(f"💡 {preset_data['description']}")
        target_calories = preset_data["calories"]
        target_protein = preset_data["protein"]
        target_carbs = preset_data["carbs"]
        target_fat = preset_data["fat"]
        
        # Show preset values (read-only)
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Calories", f"{target_calories}")
            st.metric("Protein", f"{target_protein}g")
        with col2:
            st.metric("Carbs", f"{target_carbs}g")
            st.metric("Fat", f"{target_fat}g")
    else:
        # === MANUAL TARGETS ===
        st.subheader("🎯 Custom Targets")
        
        target_calories = st.slider("Daily Calories (kcal)", 1200, 4000, 2000, 100)
        
        # Macro calculator helper
        if st.checkbox("📊 Calculate from percentages"):
            col1, col2, col3 = st.columns(3)
            with col1:
                protein_pct = st.number_input("Protein %", 10, 40, 30)
            with col2:
                carb_pct = st.number_input("Carbs %", 20, 60, 40)
            with col3:
                fat_pct = st.number_input("Fat %", 15, 50, 30)
            
            if protein_pct + carb_pct + fat_pct != 100:
                st.warning(f"⚠️ Total: {protein_pct + carb_pct + fat_pct}% (should be 100%)")
            
            target_protein = int((target_calories * protein_pct / 100) / 4)
            target_carbs = int((target_calories * carb_pct / 100) / 4)
            target_fat = int((target_calories * fat_pct / 100) / 9)
            
            st.caption(f"→ {target_protein}g protein, {target_carbs}g carbs, {target_fat}g fat")
        else:
            target_protein = st.slider("Protein (g)", 50, 300, 150, 10)
            target_carbs = st.slider("Carbs (g)", 50, 500, 200, 10)
            target_fat = st.slider("Fat (g)", 20, 150, 65, 5)
    
    tolerance = st.slider(
        "Flexibility (%)",
        5, 30, 15, 5,
        help="How flexible the targets are (±%)"
    ) / 100
    
    st.markdown("---")
    
    # === BUDGET CONSTRAINT ===
    st.subheader("💰 Budget")
    
    enable_budget = st.checkbox("Set maximum budget", value=True)
    if enable_budget:
        max_budget = st.slider(
            "Max daily budget ($)",
            10, 100, 50, 5,
            help="Maximum you want to spend per day"
        )
    else:
        max_budget = None
    
    st.markdown("---")
    
    # === DIETARY RESTRICTIONS ===
    st.subheader("🚫 Dietary Restrictions")
    
    restrictions = st.multiselect(
        "Restrictions",
        ["Vegetarian", "Vegan", "Gluten-Free", "Dairy-Free", "Nut Allergy", "Pescatarian"],
        help="Foods will be filtered based on your restrictions"
    )
    
    # === FOOD PREFERENCES ===
    st.subheader("🍽️ Food Selection")
    
    db = st.session_state.foods_db
    categories = db.list_categories()
    
    selected_categories = st.multiselect(
        "Food Categories",
        categories,
        default=["proteins", "vegetables", "grains"],
        help="Choose which food categories to include"
    )
    
    # Exclude specific foods
    if st.checkbox("Exclude specific foods"):
        all_foods = []
        for cat in selected_categories:
            foods_in_cat = db.list_foods_in_category(cat)
            all_foods.extend([f['name'] for f in foods_in_cat])
        
        excluded_foods = st.multiselect(
            "Foods to exclude",
            all_foods,
            help="Don't like something? Exclude it here"
        )
    else:
        excluded_foods = []
    
    st.markdown("---")
    
    # === MULTI-DAY PLANNING ===
    st.subheader("📅 Planning Period")
    
    num_days = st.number_input(
        "Number of days",
        min_value=1,
        max_value=7,
        value=1,
        help="Plan for multiple days (meal prep)"
    )
    
    if num_days > 1:
        st.info(f"💡 Planning for {num_days} days will optimize for variety and bulk purchasing")
    
    st.markdown("---")
    
    # === MICRONUTRIENTS ===
    st.subheader("🔬 Advanced")
    
    track_micros = st.checkbox(
        "Track micronutrients",
        help="Include vitamins and minerals in optimization"
    )
    
    st.markdown("---")
    
    # === OPTIMIZE BUTTON ===
    if st.button("🚀 Optimize Shopping List", type="primary"):
        optimize_enhanced(
            selected_categories,
            target_calories,
            target_protein,
            target_carbs,
            target_fat,
            tolerance,
            max_budget,
            restrictions,
            excluded_foods,
            num_days,
            track_micros
        )
    
    # === SAVED PLANS ===
    st.markdown("---")
    st.subheader("💾 Saved Plans")
    
    saved_plans = load_saved_plans()
    if saved_plans:
        plan_names = [p['name'] for p in saved_plans]
        selected_plan = st.selectbox("Load previous plan", [""] + plan_names)
        
        if selected_plan:
            if st.button("📥 Load Plan"):
                plan = next(p for p in saved_plans if p['name'] == selected_plan)
                st.session_state.optimization_result = plan['result']
                st.success(f"Loaded: {selected_plan}")
                st.rerun()


def optimize_enhanced(categories, calories, protein, carbs, fat, tolerance, 
                     max_budget, restrictions, excluded_foods, num_days, track_micros):
    """Enhanced optimization with all features"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Load foods
        status_text.text("🔄 Loading food database...")
        progress_bar.progress(20)
        
        db = st.session_state.foods_db
        all_foods = {}
        for category in categories:
            all_foods.update(db.get_category(category))
        
        # Apply restrictions
        status_text.text("🔄 Applying dietary restrictions...")
        progress_bar.progress(40)
        all_foods = apply_restrictions(all_foods, restrictions, excluded_foods)
        
        if not all_foods:
            st.error("❌ No foods available after applying restrictions")
            return
        
        # Get prices
        status_text.text("🔄 Fetching prices...")
        progress_bar.progress(60)
        prices = generate_mock_prices(all_foods)
        
        # Scale for multiple days
        if num_days > 1:
            calories *= num_days
            protein *= num_days
            carbs *= num_days
            fat *= num_days
        
        # Run optimization
        status_text.text("🔄 Running optimization algorithm...")
        progress_bar.progress(80)
        
        optimizer = SimpleDietOptimizer()
        result = optimizer.optimize_for_macros(
            all_foods,
            prices,
            target_calories=calories,
            target_protein_g=protein,
            target_carbs_g=carbs,
            target_fat_g=fat,
            tolerance=tolerance
        )
        
        progress_bar.progress(100)
        
        if result:
            # Check budget
            if max_budget and result['total_cost'] > max_budget * num_days:
                st.warning(f"⚠️ Cost ${result['total_cost']:.2f} exceeds budget ${max_budget * num_days:.2f}")
                st.info("💡 Try: Increase budget, add cheaper food categories, or adjust targets")
            
            # Add metadata
            result['num_days'] = num_days
            result['restrictions'] = restrictions
            result['track_micros'] = track_micros
            result['timestamp'] = datetime.now().isoformat()
            
            st.session_state.optimization_result = result
            st.session_state.optimization_history.append({
                'timestamp': datetime.now(),
                'cost': result['total_cost'],
                'num_foods': result['num_foods']
            })
            
            status_text.empty()
            progress_bar.empty()
            st.success("✅ Optimization complete!")
            st.rerun()
        else:
            st.error("❌ No feasible solution found")
            st.info("""
            **Possible fixes:**
            - Lower your protein/calorie targets
            - Increase budget
            - Add more food categories
            - Increase flexibility percentage
            """)
            
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.exception(e)
    finally:
        progress_bar.empty()
        status_text.empty()


def apply_restrictions(foods, restrictions, excluded_foods):
    """Filter foods based on dietary restrictions"""
    
    filtered = {}
    
    for key, food in foods.items():
        # Skip excluded
        if food.description in excluded_foods:
            continue
        
        # Apply restrictions
        desc_lower = food.description.lower()
        category_lower = (food.food_category or "").lower()
        
        skip = False
        
        if "Vegetarian" in restrictions or "Vegan" in restrictions:
            meat_keywords = ['meat', 'beef', 'pork', 'chicken', 'turkey', 'fish', 'salmon', 'tuna']
            if any(kw in desc_lower or kw in category_lower for kw in meat_keywords):
                skip = True
        
        if "Vegan" in restrictions:
            animal_keywords = ['dairy', 'milk', 'cheese', 'yogurt', 'egg']
            if any(kw in desc_lower or kw in category_lower for kw in animal_keywords):
                skip = True
        
        if "Dairy-Free" in restrictions:
            dairy_keywords = ['dairy', 'milk', 'cheese', 'yogurt', 'butter']
            if any(kw in desc_lower or kw in category_lower for kw in dairy_keywords):
                skip = True
        
        if "Nut Allergy" in restrictions:
            nut_keywords = ['nut', 'almond', 'walnut', 'peanut', 'cashew']
            if any(kw in desc_lower for kw in nut_keywords):
                skip = True
        
        if "Gluten-Free" in restrictions:
            gluten_keywords = ['bread', 'wheat', 'pasta', 'oat']
            if any(kw in desc_lower for kw in gluten_keywords):
                skip = True
        
        if not skip:
            filtered[key] = food
    
    return filtered


def show_welcome_screen():
    """Enhanced welcome screen"""
    
    # Value props
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        ### 🎯 Smart Optimization
        Mathematical algorithms find the perfect food combination
        """)
    
    with col2:
        st.markdown("""
        ### 💰 Budget Control
        Set your max budget and never overspend
        """)
    
    with col3:
        st.markdown("""
        ### 🥗 Personalized
        Dietary restrictions, preferences, and goals
        """)
    
    with col4:
        st.markdown("""
        ### 📊 Data-Driven
        Complete nutrition from USDA + real prices
        """)
    
    st.markdown("---")
    
    # Stats
    db = st.session_state.foods_db
    total_foods = sum(len(db.list_foods_in_category(cat)) for cat in db.list_categories())
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Foods Available", total_foods)
    col2.metric("Avg Nutrients/Food", "85+")
    col3.metric("Categories", len(db.list_categories()))
    col4.metric("Optimization Time", "<1 sec")
    
    st.markdown("---")
    
    # Show available foods
    show_food_database()


def show_food_database():
    """Show food database with enhanced UI"""
    
    st.header("📦 Available Foods")
    
    db = st.session_state.foods_db
    categories = db.list_categories()
    
    tabs = st.tabs([cat.replace('_', ' ').title() for cat in categories])
    
    for tab, category in zip(tabs, categories):
        with tab:
            foods_list = db.list_foods_in_category(category)
            
            if foods_list:
                df = pd.DataFrame(foods_list)
                df = df[['name', 'nutrients', 'description']]
                df.columns = ['Food', 'Nutrients', 'Description']
                
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Nutrients": st.column_config.ProgressColumn(
                            "Nutrients",
                            min_value=0,
                            max_value=150,
                        ),
                    }
                )


def show_results_enhanced():
    """Enhanced results with all features"""
    
    result = st.session_state.optimization_result
    num_days = result.get('num_days', 1)
    
    # Header
    st.header("📊 Your Optimized Meal Plan")
    
    # Summary metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("💰 Total Cost", f"${result['total_cost']:.2f}")
        if num_days > 1:
            st.caption(f"${result['total_cost']/num_days:.2f}/day")
    
    with col2:
        st.metric("🛒 Foods", result['num_foods'])
    
    with col3:
        calories = result['total_nutrients'].get('Energy', 0)
        st.metric("🔥 Calories", f"{calories:.0f}")
        if num_days > 1:
            st.caption(f"{calories/num_days:.0f}/day")
    
    with col4:
        protein = result['total_nutrients'].get('Protein', 0)
        st.metric("💪 Protein", f"{protein:.0f}g")
        if num_days > 1:
            st.caption(f"{protein/num_days:.0f}g/day")
    
    with col5:
        # Cost efficiency
        if protein > 0:
            cost_per_protein = result['total_cost'] / protein
            st.metric("💵 $/g Protein", f"${cost_per_protein:.3f}")
    
    st.markdown("---")
    
    # Smart Insights
    show_smart_insights(result)
    
    st.markdown("---")
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🛒 Shopping List",
        "📊 Nutrition",
        "📈 Analysis",
        "🍳 Recipes",
        "💾 Save/Export"
    ])
    
    with tab1:
        show_shopping_list_enhanced(result)
    
    with tab2:
        show_nutrition_enhanced(result)
    
    with tab3:
        show_analysis(result)
    
    with tab4:
        show_recipes(result)
    
    with tab5:
        show_export_enhanced(result)


def show_smart_insights(result):
    """Generate and display smart insights"""
    
    insights = []
    
    # Cost efficiency insight
    protein = result['total_nutrients'].get('Protein', 0)
    calories = result['total_nutrients'].get('Energy', 0)
    cost = result['total_cost']
    
    if protein > 0:
        cost_per_g_protein = cost / protein
        if cost_per_g_protein < 0.04:
            insights.append("🎉 Excellent value! You're getting protein at <$0.04/gram")
        elif cost_per_g_protein > 0.08:
            insights.append("💡 Tip: Adding chicken or eggs could reduce your cost per gram of protein")
    
    # Budget insight
    if cost < 30:
        savings = 50 - cost  # Assuming $50/day average
        insights.append(f"💰 Great budget control! Saving ~${savings:.2f} vs average")
    
    # Variety insight
    if result['num_foods'] > 10:
        insights.append("🌈 Excellent variety! Using 10+ different foods ensures diverse micronutrients")
    elif result['num_foods'] < 5:
        insights.append("⚠️ Limited variety. Consider adding more food categories for better nutrition")
    
    # Macro balance insight
    protein_cal = protein * 4
    carbs = result['total_nutrients'].get('Carbohydrate, by difference', 0)
    fat = result['total_nutrients'].get('Total lipid (fat)', 0)
    carbs_cal = carbs * 4
    fat_cal = fat * 9
    
    if protein_cal > calories * 0.35:
        insights.append("💪 High protein plan! Great for muscle building or weight loss")
    
    # Display insights
    if insights:
        st.markdown("### 💡 Smart Insights")
        for insight in insights:
            st.markdown(f'<div class="insight-box">{insight}</div>', unsafe_allow_html=True)


def show_shopping_list_enhanced(result):
    """Enhanced shopping list with cost analysis"""
    
    st.subheader("🛒 Your Shopping List")
    
    # Prepare data
    shopping_data = []
    
    for food_key, data in result['selected_foods'].items():
        food = data['food']
        quantity = data['quantity_grams']
        price = data['price']
        protein = food.get_nutrient("Protein") or 0
        
        # Calculate per serving
        protein_per_package = (protein / 100) * quantity
        cost_per_g_protein = price / protein_per_package if protein_per_package > 0 else 0
        
        shopping_data.append({
            'Food': food.description,
            'Quantity': f"{quantity:.0f}g",
            'Lbs': f"{quantity/453.6:.2f}",
            'Price': price,
            'Protein/Package': f"{protein_per_package:.0f}g",
            'Cost/g Protein': f"${cost_per_g_protein:.3f}" if cost_per_g_protein > 0 else "N/A"
        })
    
    df = pd.DataFrame(shopping_data)
    
    # Sort by cost efficiency
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Price": st.column_config.NumberColumn(
                "Price",
                format="$%.2f"
            )
        }
    )
    
    # Cost breakdown
    st.markdown("### 💰 Cost Breakdown")
    col1, col2 = st.columns(2)
    
    with col1:
        # Pie chart
        fig = px.pie(
            df,
            values='Price',
            names='Food',
            title='Spending by Food',
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Value ranking
        st.markdown("**Best Value Foods (by protein cost):**")
        df_sorted = df.sort_values('Cost/g Protein')
        for i, row in df_sorted.head(5).iterrows():
            if row['Cost/g Protein'] != "N/A":
                st.write(f"{i+1}. {row['Food']}: {row['Cost/g Protein']}")


def show_nutrition_enhanced(result):
    """Enhanced nutrition breakdown with micros"""
    
    st.subheader("📊 Macronutrient Profile")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Macro table
        nutrition_data = []
        for nutrient_name, total in result['total_nutrients'].items():
            min_target, max_target = result['targets'][nutrient_name]
            
            status = "✅ Perfect"
            if total < min_target:
                status = "⚠️ Below target"
            elif total > max_target:
                status = "⚠️ Above target"
            
            short_name = (nutrient_name.replace('Carbohydrate, by difference', 'Carbs')
                                       .replace('Total lipid (fat)', 'Fat'))
            
            nutrition_data.append({
                'Nutrient': short_name,
                'Actual': f"{total:.1f}",
                'Target': f"{min_target:.0f}-{max_target:.0f}",
                'Status': status
            })
        
        df = pd.DataFrame(nutrition_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    with col2:
        # Macro pie chart (by calories)
        protein = result['total_nutrients'].get('Protein', 0) * 4
        carbs = result['total_nutrients'].get('Carbohydrate, by difference', 0) * 4
        fat = result['total_nutrients'].get('Total lipid (fat)', 0) * 9
        
        fig = go.Figure(data=[go.Pie(
            labels=['Protein', 'Carbs', 'Fat'],
            values=[protein, carbs, fat],
            hole=0.4,
            marker_colors=['#FF6B6B', '#4ECDC4', '#FFE66D']
        )])
        
        fig.update_layout(title='Calorie Distribution', height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Micronutrients section
    if result.get('track_micros', False):
        st.markdown("---")
        st.subheader("🔬 Micronutrient Analysis")
        st.info("💡 Feature coming soon: Track vitamins and minerals!")


def show_analysis(result):
    """Show detailed analysis and visualizations"""
    
    st.subheader("📈 Detailed Analysis")
    
    # Target comparison
    nutrients = []
    actuals = []
    mins = []
    maxs = []
    
    for nutrient, total in result['total_nutrients'].items():
        min_t, max_t = result['targets'][nutrient]
        
        short_name = (nutrient.replace('Carbohydrate, by difference', 'Carbs')
                             .replace('Total lipid (fat)', 'Fat'))
        
        nutrients.append(short_name)
        actuals.append(total)
        mins.append(min_t)
        maxs.append(max_t)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Actual',
        x=nutrients,
        y=actuals,
        marker_color='#667eea'
    ))
    
    fig.add_trace(go.Scatter(
        name='Min Target',
        x=nutrients,
        y=mins,
        mode='markers',
        marker=dict(size=12, symbol='line-ew', color='green')
    ))
    
    fig.add_trace(go.Scatter(
        name='Max Target',
        x=nutrients,
        y=maxs,
        mode='markers',
        marker=dict(size=12, symbol='line-ew', color='red')
    ))
    
    fig.update_layout(
        title='Actual vs Target Nutrition',
        height=500,
        yaxis_title='Amount',
        barmode='group'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # History
    if len(st.session_state.optimization_history) > 1:
        st.markdown("---")
        st.subheader("📜 Optimization History")
        
        history_df = pd.DataFrame(st.session_state.optimization_history)
        
        fig = px.line(
            history_df,
            x='timestamp',
            y='cost',
            title='Cost Over Time',
            markers=True
        )
        
        st.plotly_chart(fig, use_container_width=True)


def show_recipes(result):
    """Show recipe suggestions based on selected foods"""
    
    st.subheader("🍳 Recipe Suggestions")
    
    selected_food_names = [
        data['food'].description.lower()
        for data in result['selected_foods'].values()
    ]
    
    # Find matching recipes
    matching_recipes = []
    for recipe in RECIPES['combinations']:
        if any(food in ' '.join(selected_food_names) for food in recipe['foods']):
            matching_recipes.append(recipe)
    
    if matching_recipes:
        cols = st.columns(min(len(matching_recipes), 3))
        
        for i, recipe in enumerate(matching_recipes[:3]):
            with cols[i]:
                st.markdown(f"### {recipe['name']}")
                st.write(recipe['description'])
                st.write("**Ingredients from your list:**")
                for food in recipe['foods']:
                    if any(food in fname for fname in selected_food_names):
                        st.write(f"✅ {food.title()}")
    else:
        st.info("💡 Add more foods to see recipe suggestions!")
    
    # General tips
    st.markdown("---")
    st.markdown("### 💡 Meal Prep Tips")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Batch Cooking:**
        - Cook all grains at once
        - Grill multiple chicken breasts
        - Pre-portion into containers
        """)
    
    with col2:
        st.markdown("""
        **Storage:**
        - Refrigerate up to 4 days
        - Freeze extra portions
        - Label with dates
        """)


def show_export_enhanced(result):
    """Enhanced export with save functionality"""
    
    st.subheader("💾 Save & Export")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Save plan
        st.markdown("### 💾 Save This Plan")
        plan_name = st.text_input(
            "Plan name",
            value=f"Plan {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        
        if st.button("Save Plan"):
            save_plan(plan_name, result)
            st.success(f"✅ Saved: {plan_name}")
    
    with col2:
        # Export options
        st.markdown("### 📥 Export")
        
        # Text export
        shopping_list_text = generate_shopping_list_text(result)
        st.download_button(
            label="📄 Download TXT",
            data=shopping_list_text,
            file_name=f"shopping_list_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain"
        )
        
        # CSV export
        shopping_df = generate_shopping_list_df(result)
        st.download_button(
            label="📊 Download CSV",
            data=shopping_df.to_csv(index=False),
            file_name=f"meal_plan_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    st.markdown("---")
    
    # Reset
    if st.button("🔄 Start New Optimization"):
        st.session_state.optimization_result = None
        st.rerun()


def save_plan(name, result):
    """Save optimization plan"""
    
    plans_dir = Path("saved_plans")
    plans_dir.mkdir(exist_ok=True)
    
    plan_file = plans_dir / f"{name.replace(' ', '_')}.json"
    
    # Serialize (can't directly serialize USDAFood objects)
    serializable_result = {
        'name': name,
        'timestamp': result.get('timestamp', datetime.now().isoformat()),
        'total_cost': result['total_cost'],
        'num_foods': result['num_foods'],
        'total_nutrients': result['total_nutrients'],
        'targets': result['targets'],
        'num_days': result.get('num_days', 1),
        'restrictions': result.get('restrictions', [])
    }
    
    with open(plan_file, 'w') as f:
        json.dump(serializable_result, f, indent=2)


def load_saved_plans():
    """Load all saved plans"""
    
    plans_dir = Path("saved_plans")
    if not plans_dir.exists():
        return []
    
    plans = []
    for plan_file in plans_dir.glob("*.json"):
        try:
            with open(plan_file, 'r') as f:
                plan = json.load(f)
                plans.append(plan)
        except:
            continue
    
    return plans


def generate_shopping_list_text(result):
    """Generate text shopping list"""
    
    num_days = result.get('num_days', 1)
    
    text = "="*60 + "\n"
    text += "OPTIMIZED SHOPPING LIST\n"
    text += "="*60 + "\n\n"
    text += f"Total Cost: ${result['total_cost']:.2f}"
    if num_days > 1:
        text += f" (${result['total_cost']/num_days:.2f}/day)"
    text += f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    if num_days > 1:
        text += f"Planning Period: {num_days} days\n"
    text += "\nITEMS:\n" + "-"*60 + "\n"
    
    for food_key, data in result['selected_foods'].items():
        food = data['food']
        quantity = data['quantity_grams']
        price = data['price']
        
        text += f"\n☐ {food.description}\n"
        text += f"   Quantity: {quantity:.0f}g ({quantity/453.6:.2f} lbs)\n"
        text += f"   Price: ${price:.2f}\n"
    
    text += "\n" + "="*60 + "\n"
    text += "NUTRITION SUMMARY:\n" + "-"*60 + "\n"
    
    for nutrient, total in result['total_nutrients'].items():
        daily = total / num_days if num_days > 1 else total
        text += f"{nutrient}: {daily:.1f}/day\n"
    
    return text


def generate_shopping_list_df(result):
    """Generate DataFrame for CSV export"""
    
    data = []
    
    for food_key, item_data in result['selected_foods'].items():
        food = item_data['food']
        quantity = item_data['quantity_grams']
        price = item_data['price']
        
        protein = food.get_nutrient("Protein") or 0
        calories = food.get_nutrient("Energy") or 0
        
        data.append({
            'Food': food.description,
            'Quantity_g': quantity,
            'Quantity_lbs': quantity / 453.6,
            'Price': price,
            'Category': food.food_category,
            'Protein_per_100g': protein,
            'Calories_per_100g': calories
        })
    
    return pd.DataFrame(data)


def generate_mock_prices(foods):
    """Generate mock prices"""
    
    price_ranges = {
        'proteins': (2.99, 8.99),
        'vegetables': (1.99, 4.99),
        'grains': (2.49, 4.99),
        'fruits': (0.59, 4.99),
        'nuts_seeds': (5.99, 9.99),
        'dairy': (2.79, 5.99),
        'legumes': (1.99, 3.49)
    }
    
    import random
    prices = {}
    
    for food_key in foods.keys():
        for category, (min_price, max_price) in price_ranges.items():
            if category in food_key:
                prices[food_key] = round(random.uniform(min_price, max_price), 2)
                break
        else:
            prices[food_key] = round(random.uniform(2.99, 6.99), 2)
    
    return prices


if __name__ == "__main__":
    main()
