import json
import asyncio
import os
import base64
from typing import List, Optional
from io import BytesIO
from PIL import Image
from google import genai
from google.genai import types
from models import CoordinateItem
from prompt_loader import get_prompt_loader


class GeminiService:
    def __init__(self, api_key: Optional[str] = None):
        # Try to get API key from environment variable if not provided
        api_key = api_key or os.getenv('GOOGLE_GENAI_API_KEY')
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()

    @staticmethod
    def resize_image_base64(image_base64: str, scale: float = 0.5) -> str:
        """
        Resize image to reduce processing time for Gemini API.

        Args:
            image_base64: Base64 encoded image
            scale: Scale factor (0.5 = half resolution)

        Returns:
            str: Resized image as base64
        """
        try:
            # Decode base64 to image
            image_data = base64.b64decode(image_base64)
            image = Image.open(BytesIO(image_data))

            # Calculate new size
            new_width = int(image.width * scale)
            new_height = int(image.height * scale)

            # Resize image with high quality
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert back to base64
            buffer = BytesIO()
            resized_image.save(buffer, format=image.format or 'JPEG', quality=85)
            resized_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            print(f"[Image Resize] {image.width}x{image.height} -> {new_width}x{new_height}")
            return resized_base64
        except Exception as e:
            print(f"Error resizing image: {e}, using original")
            return image_base64
    
    def generate_recommend_reasons(self, coordinates: List[CoordinateItem]) -> str:
        """
        Generate recommendation reasons based on coordinate reviews using Gemini API.

        Args:
            coordinates: List of CoordinateItem objects (expecting 3-4 items)

        Returns:
            str: Recommendation reason text (up to 150 characters)
        """
        if not coordinates or len(coordinates) < 2:
            return ""

        # Build coordinate reviews
        coordinate_reviews = []
        for i, coord in enumerate(coordinates[:3]):  # Max 3 coordinates
            if coord.coordinate_review:
                coordinate_reviews.append(f"#コーデ{i+1}\n{coord.coordinate_review}")

        # Load prompt from file
        prompt_loader = get_prompt_loader()
        prompt = prompt_loader.format(
            "generate_recommend_reasons",
            coordinate_reviews="\n".join(coordinate_reviews)
        )
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-lite",  # Using newer model
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={"type": "object", "properties": {"recommend_reasons": {"type": "string"}}},
                    thinking_config=types.ThinkingConfig(thinking_budget=0, include_thoughts=False)
                ),
            )
            
            # Parse JSON response
            result = json.loads(response.text)
            return result.get("recommend_reasons", "")
        except Exception as e:
            print(f"Error generating recommend reasons: {e}")
            return ""
    
    async def generate_recommend_reasons_async(self, coordinates: List[CoordinateItem]) -> str:
        """
        Async version of generate_recommend_reasons.
        """
        # Run the synchronous method in an executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate_recommend_reasons, coordinates)
    
    def chat_coordinate_advice(self, question: str, gender: str, model: Optional[str] = None) -> str:
        """
        Generate coordinate advice based on user's question using Gemini API.

        Args:
            question: User's question about fashion/coordination
            gender: Gender of the user (men/women/other)

        Returns:
            str: Fashion advice response
        """
        gender_str = "メンズ" if gender == "men" else "レディース" if gender == "women" else "ユニセックス"

        # Load prompt from file
        prompt_loader = get_prompt_loader()
        prompt = prompt_loader.format(
            "chat_coordinate_advice",
            gender_str=gender_str,
            question=question
        )
        
        try:
            # Use provided model or default to gemini-2.5-flash-lite
            model_name = model if model else "gemini-2.5-flash-lite"
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={"type": "object", "properties": {"answer": {"type": "string"}}},
                    temperature=0.7,
                    max_output_tokens=3000,
                    thinking_config=types.ThinkingConfig(thinking_budget=0, include_thoughts=False)
                ),
            )
            
            result = json.loads(response.text)
            return result.get("answer", "申し訳ございません。回答を生成できませんでした。")
        except Exception as e:
            print(f"Error in chat_coordinate_advice: {e}")
            return "申し訳ございません。エラーが発生しました。もう一度お試しください。"
    
    def chat_coordinate_advice_with_image(self, question: str, gender: str, image_base64: str, model: Optional[str] = None) -> str:
        """
        Generate coordinate advice based on user's question and image using Gemini API.

        Args:
            question: User's question about fashion/coordination
            gender: Gender of the user (men/women/other)
            image_base64: Base64 encoded image data

        Returns:
            str: Fashion advice response
        """
        gender_str = "メンズ" if gender == "men" else "レディース" if gender == "women" else "ユニセックス"

        # Load prompt from file
        prompt_loader = get_prompt_loader()
        prompt = prompt_loader.format(
            "chat_coordinate_advice_with_image",
            gender_str=gender_str,
            question=question
        )
        
        try:
            # Resize image to 1/2 resolution for faster processing
            resized_image_base64 = self.resize_image_base64(image_base64, scale=0.5)

            # Create content with text and resized image
            content = [
                {"text": prompt},
                {"inline_data": {
                    "mime_type": "image/jpeg",
                    "data": resized_image_base64
                }}
            ]

            # Use provided model or default to gemini-2.5-flash-lite
            model_name = model if model else "gemini-2.5-flash-lite"
            response = self.client.models.generate_content(
                model=model_name,
                contents=content,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={"type": "object", "properties": {"answer": {"type": "string"}}},
                    temperature=0.7,
                    max_output_tokens=3000,
                    thinking_config=types.ThinkingConfig(thinking_budget=0, include_thoughts=False)
                ),
            )
            
            result = json.loads(response.text)
            return result.get("answer", "申し訳ございません。回答を生成できませんでした。")
        except Exception as e:
            print(f"Error in chat_coordinate_advice_with_image: {e}")
            return "申し訳ございません。エラーが発生しました。もう一度お試しください。"
    
    async def chat_coordinate_advice_async(self, question: str, gender: str, image_base64: Optional[str] = None, model: Optional[str] = None) -> str:
        """
        Async version of chat_coordinate_advice with optional image support.
        """
        loop = asyncio.get_event_loop()
        if image_base64:
            return await loop.run_in_executor(None, self.chat_coordinate_advice_with_image, question, gender, image_base64, model)
        else:
            return await loop.run_in_executor(None, self.chat_coordinate_advice, question, gender, model)

    def _generate_review_parallel(self, resized_image_base64: str) -> dict:
        """
        並列処理用: レビューとキャッチフレーズを生成

        Returns:
            dict: {"ai_catchphrase": str, "ai_review_comment": str}
        """
        # Load prompt from file
        prompt_loader = get_prompt_loader()
        prompt = prompt_loader.load("generate_review_parallel")

        try:
            content = [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": resized_image_base64}}
            ]

            response = self.client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=content,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "ai_catchphrase": {"type": "string"},
                            "ai_review_comment": {"type": "string"}
                        },
                        "required": ["ai_catchphrase", "ai_review_comment"]
                    },
                    temperature=0.5,
                    max_output_tokens=500,
                    thinking_config=types.ThinkingConfig(thinking_budget=0, include_thoughts=False)
                ),
            )

            return json.loads(response.text)
        except Exception as e:
            print(f"[Parallel 1] Error generating review: {e}")
            return {
                "ai_catchphrase": "素敵なコーディネート",
                "ai_review_comment": "バランスの取れた素敵なコーディネートです。"
            }

    def _generate_tags_parallel(self, resized_image_base64: str) -> dict:
        """
        並列処理用: タグを生成

        Returns:
            dict: {"tags": list}
        """
        # Load prompt from file
        prompt_loader = get_prompt_loader()
        prompt = prompt_loader.load("generate_tags_parallel")

        try:
            content = [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": resized_image_base64}}
            ]

            response = self.client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=content,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "tags": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["tags"]
                    },
                    temperature=0.7,
                    max_output_tokens=300,
                    thinking_config=types.ThinkingConfig(thinking_budget=0, include_thoughts=False)
                ),
            )

            return json.loads(response.text)
        except Exception as e:
            print(f"[Parallel 2] Error generating tags: {e}")
            return {"tags": ["カジュアル", "シンプル", "ベーシック", "ナチュラル", "デイリー", "トップス", "ボトムス"]}

    def _extract_items_parallel(self, resized_image_base64: str) -> dict:
        """
        並列処理用: アイテムを抽出

        Returns:
            dict: {"items": list, "item_types": list}
        """
        # Load prompt from file
        prompt_loader = get_prompt_loader()
        prompt = prompt_loader.load("extract_items_parallel")

        try:
            content = [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": resized_image_base64}}
            ]

            response = self.client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=content,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "item_types": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "item_type": {
                                            "type": "string",
                                            "enum": ["アウター", "トップス", "ボトムス", "シューズ", "アクセサリー"]
                                        },
                                        "category": {"type": "string"},
                                        "color": {"type": "string"},
                                        "description": {"type": "string"}
                                    },
                                    "required": ["item_type", "category", "color", "description"]
                                }
                            }
                        },
                        "required": ["items", "item_types"]
                    },
                    temperature=0.4,
                    max_output_tokens=700,
                    thinking_config=types.ThinkingConfig(thinking_budget=0, include_thoughts=False)
                ),
            )

            return json.loads(response.text)
        except Exception as e:
            print(f"[Parallel 3] Error extracting items: {e}")
            return {"items": [], "item_types": []}

    def generate_fashion_review(self, image_base64: str) -> dict:
        """
        Generate comprehensive fashion review and extract items from full-body image using Gemini API.
        Uses parallel requests to improve response time.

        Args:
            image_base64: Base64 encoded full-body image

        Returns:
            dict: {
                "ai_catchphrase": str,
                "ai_review_comment": str,
                "tags": list,
                "item_types": list,
                "items": list
            }
        """
        import time
        start_time = time.time()

        # Resize image to 30% resolution for faster processing
        resized_image_base64 = self.resize_image_base64(image_base64, scale=0.3)

        # Execute 3 parallel requests using ThreadPoolExecutor
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all 3 requests in parallel
            future_review = executor.submit(self._generate_review_parallel, resized_image_base64)
            future_tags = executor.submit(self._generate_tags_parallel, resized_image_base64)
            future_items = executor.submit(self._extract_items_parallel, resized_image_base64)

            # Wait for all results
            review_result = future_review.result()
            tags_result = future_tags.result()
            items_result = future_items.result()

        # Merge results
        result = {
            "ai_catchphrase": review_result.get("ai_catchphrase", ""),
            "ai_review_comment": review_result.get("ai_review_comment", ""),
            "tags": tags_result.get("tags", []),
            "item_types": items_result.get("item_types", []),
            "items": items_result.get("items", [])
        }

        elapsed_time = time.time() - start_time
        print(f"[Gemini Parallel] Fashion review completed in {elapsed_time:.2f}s with {len(result.get('items', []))} items")

        return result

    async def generate_fashion_review_async(self, image_base64: str) -> dict:
        """
        Async version of generate_fashion_review with parallel processing.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate_fashion_review, image_base64)

    def extract_coordinate_items(self, image_base64: str) -> list:
        """
        Extract items from coordinate image using Gemini API.

        Args:
            image_base64: Base64 encoded full-body coordinate image

        Returns:
            list: List of items with properties:
                - item_type: Type of item (アウター, トップス, ボトムス, シューズ, アクセサリー)
                - category: Specific category (e.g., Tシャツ, ジーンズ, スニーカー)
                - color: Primary color of the item
                - description: Generated tags based on color and type
        """
        # Resize image to 1/2 resolution for faster processing
        resized_image_base64 = self.resize_image_base64(image_base64, scale=0.5)

        # Response schema definition
        response_schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_type": {
                                "type": "string",
                                "enum": ["アウター", "トップス", "ボトムス", "シューズ", "アクセサリー"]
                            },
                            "category": {"type": "string"},
                            "color": {"type": "string"},
                            "description": {
                                "type": "string",
                                "description": "色と種類からタグを生成してください。# は含めないでください。"
                            }
                        },
                        "required": ["item_type", "category", "color", "description"]
                    }
                }
            },
            "required": ["items"]
        }

        # Load prompt from file
        prompt_loader = get_prompt_loader()
        prompt = prompt_loader.load("extract_coordinate_items")

        try:
            # Create content with text and resized image
            content = [
                {"text": prompt},
                {"inline_data": {
                    "mime_type": "image/jpeg",
                    "data": resized_image_base64
                }}
            ]

            response = self.client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=content,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    max_output_tokens=2000,
                    thinking_config=types.ThinkingConfig(thinking_budget=0, include_thoughts=False)
                ),
            )

            result = json.loads(response.text)
            items = result.get("items", [])

            print(f"[Gemini] Extracted {len(items)} items from coordinate image")
            for item in items:
                print(f"  - {item.get('item_type')}: {item.get('category')} ({item.get('color')})")

            return items

        except Exception as e:
            print(f"Error in extract_coordinate_items: {e}")
            return []

    async def extract_coordinate_items_async(self, image_base64: str) -> list:
        """
        Async version of extract_coordinate_items.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.extract_coordinate_items, image_base64)

    def analyze_recent_coordinates(self, tags_list: List[List[str]]) -> str:
        """
        Analyze recent coordinate tags and generate a summary.

        Args:
            tags_list: List of tag lists from recent coordinates (up to 3)

        Returns:
            str: Analysis summary (approximately 100 characters)
        """
        if not tags_list or all(not tags for tags in tags_list):
            return ""

        # Flatten and deduplicate tags
        all_tags = []
        for tags in tags_list:
            all_tags.extend(tags)

        if not all_tags:
            return ""

        # Load prompt from file and format with tags
        prompt_loader = get_prompt_loader()
        prompt = prompt_loader.format(
            "analyze_recent_coordinates",
            tags=', '.join(all_tags)
        )

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "analysis": {"type": "string"}
                        }
                    },
                    temperature=0.7,
                    max_output_tokens=500,
                    thinking_config=types.ThinkingConfig(thinking_budget=0, include_thoughts=False)
                ),
            )

            result = json.loads(response.text)
            return result.get("analysis", "")
        except Exception as e:
            print(f"Error in analyze_recent_coordinates: {e}")
            return ""

    async def analyze_recent_coordinates_async(self, tags_list: List[List[str]]) -> str:
        """
        Async version of analyze_recent_coordinates.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.analyze_recent_coordinates, tags_list)

    def test_gemini(self, prompt: str, model: str = "gemini-3.1-flash-lite-preview") -> str:
        """
        Simple Gemini API test with customizable model and prompt.

        Args:
            prompt: The prompt to send to Gemini
            model: The Gemini model to use

        Returns:
            str: Gemini's response
        """
        try:
            response = self.client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=500,
                    thinking_config=types.ThinkingConfig(thinking_budget=0, include_thoughts=False)
                ),
            )

            return response.text

        except Exception as e:
            print(f"Error in test_gemini: {e}")
            return f"エラーが発生しました: {str(e)}"

    async def test_gemini_async(self, prompt: str, model: str = "gemini-3.1-flash-lite-preview") -> str:
        """
        Async version of test_gemini.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.test_gemini, prompt, model)
