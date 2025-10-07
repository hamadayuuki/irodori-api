import json
import asyncio
import os
from typing import List, Optional
from google import genai
from google.genai import types
from models import CoordinateItem


class GeminiService:
    def __init__(self, api_key: Optional[str] = None):
        # Try to get API key from environment variable if not provided
        api_key = api_key or os.getenv('GOOGLE_GENAI_API_KEY')
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()
    
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
        
        # Build the prompt with coordinate reviews
        prompt_parts = ["以下にコーデの特徴を3つ渡します。出力は #アウトプットの形式 に従うこと。"]

        for i, coord in enumerate(coordinates[:3]):  # Max 4 coordinates
            if coord.coordinate_review:
                prompt_parts.append(f"#コーデ{i+1}\n{coord.coordinate_review}")   # コーデ1~3
        
        prompt_parts.append("""
            #アウトプットの形式
            {
                "recommend_reasons": "<コーデ1,2,3 をレコメンドするので、レコメンド理由を必ず150文字以内。"コーデ1,2,3"という名称を使ってはいけません。例:ブラックを基調としたミニマルなスタイルに、チェック柄のシャツを重ね着し、カジュアルさとアクセントを加えることで、単調になりがちなモノトーンコーデに深みと個性をプラスできます。また、ダメージジーンズを取り入れれば、リラックスした雰囲気を演出しつつ、都会的なブラックコーデのカジュアルダウンとしても活躍します。柄や素材感で遊ぶことで、シックな中にも抜け感と遊び心が生まれます。>"
            }
            """)
        
        prompt = "\n".join(prompt_parts)
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-lite",  # Using newer model
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={"type": "object", "properties": {"recommend_reasons": {"type": "string"}}},
                    thinking_config=types.ThinkingConfig(thinking_budget=0)  # Disables thinking
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