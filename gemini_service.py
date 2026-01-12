import json
import asyncio
import os
import base64
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
                model="gemini-2.5-flash-lite",  # Using newer model
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
        
        prompt = f"""
        あなたはプロのファッションコーディネーターです。
        以下の質問に対して、{gender_str}ファッションの観点から具体的で実用的なアドバイスを提供してください。
        
        質問: {question}
        
        回答ガイドライン:
        - 質問の内容に直接的に答える
        - 具体的なアイテムやブランドの例を挙げる
        - 季節感やトレンドを考慮する
        - シーン別の着こなし方を提案する
        - 初心者にも分かりやすい言葉で説明する
        - 150-300文字程度で簡潔にまとめる
        - 可読性を高めるために、改行コード（\n）を適宜使用する
        - また強調する箇所は **太字** にする
        - 基本的には箇条書きを使用する
        - 飽きさせない面白い言い回しで回答する
        
        # アウトプット
        {"answer": "<アドバイス内容>"}

        # アウトプットの例
        {
            "answer": "**1. ハイウエストの白ボトムス**\nロイヤルブルーの鮮やかさを最も引き立て、クリーンで爽やかな印象に。スカートやパンツ問わず、上下のメリハリを強調し、夏らしい清涼感を高めます。\n\n**2. 黒のタイトスカートまたはスキニーパンツ**\n黒とブルーのコントラストは、シックで大人っぽい印象を作ります。広がりのあるペプラムに対してボトムを黒で引き締めると、全体がシャープにまとまり、大人っぽく格好良いムードになります。\n\n**3. ゴールドまたはシルバーの華奢なネックレス**\n開いたデコルテラインに華奢なアクセサリーを加えることで、肌の露出感を抑えつつ、上品な輝きがプラスされます。特にゴールドはブルーをエレガントに、シルバーはクールに演出します。"
        }
        """
        
        try:
            # Use provided model or default to gemini-2.5-flash
            model_name = model if model else "gemini-2.5-flash"
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={"type": "object", "properties": {"answer": {"type": "string"}}},
                    temperature=0.7,
                    max_output_tokens=5000
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
        
        prompt = f"""
        あなたはプロのファッションコーディネーターです。
        投稿された画像を見て、以下の質問に対して{gender_str}回答してください。必要最低限の文字数で、回答ガイドラインおよびアウトプットに従って出力してください。
        
        質問: {question}
        
        回答ガイドライン（**必ず守ること**）
        - はじめに簡潔に結論を伝える
        - 初心者にも分かりやすい優しい口調で話す
        - **可読性を高めるために、改行 \n を適宜使用する**
        - **箇条書きする場合、2番目以降の行頭には2段の改行 \n\n を入れる**
        - **改行の文字は \n と表記すること。**<br>などの改行の文字として認めない
        - 強調する箇所は **太字** にする
        - 基本的には箇条書きを使用する
        
        # アウトプット
        {{"answer": "<**必ず300文字以内で**質問への回答>"}}

        # アウトプットの例
        {{"answer": "〜はーだと思います！**1. ハイウエストの白ボトムス**\nロイヤルブルーの鮮やかさを最も引き立て、クリーンで爽やかな印象に。スカートやパンツ問わず、上下のメリハリを強調し、夏らしい清涼感を高めます。\n\n**2. 黒のタイトスカートまたはスキニーパンツ**\n黒とブルーのコントラストは、シックで大人っぽい印象を作ります。広がりのあるペプラムに対してボトムを黒で引き締めると、全体がシャープにまとまり、大人っぽく格好良いムードになります。\n\n**3. ゴールドまたはシルバーの華奢なネックレス**\n開いたデコルテラインに華奢なアクセサリーを加えることで、肌の露出感を抑えつつ、上品な輝きがプラスされます。特にゴールドはブルーをエレガントに、シルバーはクールに演出します。"}}
        """
        
        try:
            # Prepare image data
            image_data = base64.b64decode(image_base64)
            
            # Create content with text and image
            content = [
                {"text": prompt},
                {"inline_data": {
                    "mime_type": "image/jpeg",
                    "data": image_base64
                }}
            ]
            
            # Use provided model or default to gemini-2.5-flash
            model_name = model if model else "gemini-2.5-flash"
            response = self.client.models.generate_content(
                model=model_name,
                contents=content,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={"type": "object", "properties": {"answer": {"type": "string"}}},
                    temperature=0.7,
                    max_output_tokens=6000
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

    def generate_fashion_review(self, image_base64: str) -> dict:
        """
        Generate comprehensive fashion review based on full-body image using Gemini API.

        Args:
            image_base64: Base64 encoded full-body image

        Returns:
            dict: {
                "ai_catchphrase": str (20-30 characters, catchy phrase),
                "ai_review_comment": str (100-200 characters, detailed review),
                "tags": list (3-5 tags describing the style)
            }
        """
        with open("prompt/coordinate-review.txt", "r", encoding="utf-8") as f:
            prompt = f.read()

        try:
            # Prepare image data
            image_data = base64.b64decode(image_base64)

            # Create content with text and image
            content = [
                {"text": prompt},
                {"inline_data": {
                    "mime_type": "image/jpeg",
                    "data": image_base64
                }}
            ]

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=content,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "ai_catchphrase": {"type": "string"},
                            "ai_review_comment": {"type": "string"},
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    },
                    temperature=0.8,
                    max_output_tokens=10000
                ),
            )

            # テキストをJSONとして読み込む (確実な方法)
            try:
                return json.loads(response.text)
            except json.JSONDecodeError:
                # 万が一JSON化に失敗した場合のフェイルセーフ
                return {
                    "ai_catchphrase": "生成エラー", 
                    "ai_review_comment": "解析できませんでした", 
                    "tags": []
                }
        except Exception as e:
            print(f"Error in generate_fashion_review: {e}")
            return {
                "ai_catchphrase": "素敵なコーディネートです！",
                "ai_review_comment": "バランスの取れた素敵なコーディネートだと思います。様々なシーンで活躍しそうですね。",
                "tags": ["カジュアル"]
            }

    async def generate_fashion_review_async(self, image_base64: str) -> dict:
        """
        Async version of generate_fashion_review.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate_fashion_review, image_base64)

