import sys
import os
from typing import Dict, Any
import joblib
from models import Gender

# Add recommend folder to Python path
recommend_folder = os.path.join(os.path.dirname(__file__), 'recommend')
sys.path.insert(0, recommend_folder)

# Import recommend function from RecommendTfidfVectorizer
from RecommendTfidfVectorizer import recommend

class RecommendService:
    _models: Dict[str, Any] = {}
    _initialized = False

    @classmethod
    def initialize(cls):
        """Initialize and load models at startup"""
        if cls._initialized:
            return

        print("Loading recommendation models...")

        # Load men's model
        men_model_path = os.path.join(recommend_folder, "men_model.joblib")
        if os.path.exists(men_model_path):
            cls._models["men"] = joblib.load(men_model_path)
            print(f"✅ Loaded men's model from {men_model_path}")
        else:
            print(f"⚠️ Men's model not found at {men_model_path}")

        # Load women's model
        women_model_path = os.path.join(recommend_folder, "women_model.joblib")
        if os.path.exists(women_model_path):
            cls._models["women"] = joblib.load(women_model_path)
            print(f"✅ Loaded women's model from {women_model_path}")
        else:
            print(f"⚠️ Women's model not found at {women_model_path}")

        cls._initialized = True
        print("Recommendation models loaded successfully")

    @classmethod
    def get_recommendations(
        cls,
        gender: Gender,
        input_type: str,
        category: str,
        text: str,
        num_outfits: int = 3,
        num_candidates: int = 5
    ) -> Dict[str, Any]:
        """
        Get coordinate recommendations based on input item

        Args:
            gender: User gender (men/women/other)
            input_type: Item type (アウター, トップス, ボトムス, シューズ, アクセサリー)
            category: Item category (e.g., ワイドパンツ)
            text: Item description text (e.g., ブラックのワイドパンツ)
            num_outfits: Number of outfit recommendations to return
            num_candidates: Number of candidates per category

        Returns:
            Dictionary containing outfit recommendations and category lists
        """
        # Initialize models if not already done
        if not cls._initialized:
            cls.initialize()

        # Select model based on gender
        # For "other" gender, default to men's model
        model_key = "men" if gender == Gender.other else gender.value

        if model_key not in cls._models:
            return {"error": f"Model not available for gender: {gender}"}

        model = cls._models[model_key]

        # Call recommend function
        try:
            result = recommend(
                model=model,
                input_type=input_type,
                category=category,
                text=text,
                num_outfits=num_outfits,
                num_candidates=num_candidates
            )
            return result
        except Exception as e:
            return {"error": f"Recommendation failed: {str(e)}"}
