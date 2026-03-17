"""
User Insight Service

ユーザーのファッションタイプと動物占い結果からインサイトを生成します。
"""

from datetime import datetime
from typing import Dict, Optional
import json
import uuid
from firebase_admin import firestore
from gemini_service import GeminiService
from prompt_loader import get_prompt_loader


class UserInsightService:
    """ユーザーインサイト生成サービス"""

    def __init__(self, db):
        """
        Initialize User Insight Service

        Args:
            db: Firestore client instance
        """
        self.db = db
        self.gemini_service = GeminiService()

    def get_latest_fashion_type(self, user_id: str) -> Optional[Dict]:
        """
        ユーザーの最新ファッションタイプ診断結果を取得

        Args:
            user_id: ユーザーID

        Returns:
            dict: ファッションタイプ診断結果 or None
        """
        try:
            # fashion-typesコレクションからドキュメントを取得（インデックス不要）
            docs = (
                self.db.collection('fashion-types')
                .where('user_id', '==', user_id)
                .stream()
            )

            # Pythonでソートして最新を取得
            all_docs = []
            for doc in docs:
                data = doc.to_dict()
                data['doc_id'] = doc.id
                all_docs.append(data)

            if not all_docs:
                return None

            # created_atでソート（降順）
            all_docs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            latest_data = all_docs[0]

            # type_codeからマスターデータを取得
            type_code = latest_data.get('type_code')
            if type_code:
                master_doc = self.db.collection('fashion-type-master').document(type_code).get()
                if master_doc.exists:
                    master_data = master_doc.to_dict()
                    return {
                        'type_code': type_code,
                        'type_name': master_data.get('type_name'),
                        'description': master_data.get('description'),
                        'core_stance': master_data.get('core_stance'),
                        'group': master_data.get('group'),
                        'group_color': master_data.get('group_color'),
                        'scores': {
                            'trend_score': latest_data.get('trend_score'),
                            'self_score': latest_data.get('self_score'),
                            'social_score': latest_data.get('social_score'),
                            'function_score': latest_data.get('function_score'),
                            'economy_score': latest_data.get('economy_score')
                        }
                    }
            return None
        except Exception as e:
            print(f"[UserInsight] Error fetching fashion type: {e}")
            return None

    def get_latest_animal_fortune(self, user_id: str) -> Optional[Dict]:
        """
        ユーザーの最新動物占い結果を取得

        Args:
            user_id: ユーザーID

        Returns:
            dict: 動物占い結果 or None
        """
        try:
            # animal-fortunesコレクションからドキュメントを取得（インデックス不要）
            docs = (
                self.db.collection('animal-fortunes')
                .where('user_id', '==', user_id)
                .stream()
            )

            # Pythonでソートして最新を取得
            all_docs = []
            for doc in docs:
                data = doc.to_dict()
                data['doc_id'] = doc.id
                all_docs.append(data)

            if not all_docs:
                return None

            # created_atでソート（降順）
            all_docs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            latest_data = all_docs[0]

            # animal_numberからマスターデータを取得
            animal_number = latest_data.get('animal_number')
            if animal_number:
                master_doc = self.db.collection('animal-master').document(str(animal_number)).get()
                if master_doc.exists:
                    master_data = master_doc.to_dict()
                    return {
                        'animal_number': animal_number,
                        'animal': master_data.get('animal'),
                        'animal_name': master_data.get('animal_name'),
                        'base_personality': master_data.get('base_personality', latest_data.get('base_personality')),
                        'life_tendency': master_data.get('life_tendency', latest_data.get('life_tendency')),
                        'female_feature': master_data.get('female_feature', latest_data.get('female_feature')),
                        'male_feature': master_data.get('male_feature', latest_data.get('male_feature')),
                        'love_tendency': master_data.get('love_tendency', latest_data.get('love_tendency'))
                    }
                else:
                    # マスターデータがない場合、ユーザーデータをそのまま使用
                    return {
                        'animal_number': animal_number,
                        'animal': latest_data.get('animal'),
                        'animal_name': latest_data.get('animal_name'),
                        'base_personality': latest_data.get('base_personality'),
                        'life_tendency': latest_data.get('life_tendency'),
                        'female_feature': latest_data.get('female_feature'),
                        'male_feature': latest_data.get('male_feature'),
                        'love_tendency': latest_data.get('love_tendency')
                    }
            return None
        except Exception as e:
            print(f"[UserInsight] Error fetching animal fortune: {e}")
            return None

    def generate_insight(self, user_id: str) -> Dict:
        """
        ユーザーのインサイトを生成してFirestoreに保存

        Args:
            user_id: ユーザーID

        Returns:
            dict: {
                "status": str,
                "user_id": str,
                "insight_id": str,
                "fashion_type": dict,
                "animal_fortune": dict,
                "insight": str,
                "generated_at": str
            }
        """
        # ファッションタイプと動物占い結果を取得
        fashion_type = self.get_latest_fashion_type(user_id)
        animal_fortune = self.get_latest_animal_fortune(user_id)

        # データが存在しない場合
        if not fashion_type and not animal_fortune:
            return {
                "status": "no_data",
                "user_id": user_id,
                "insight_id": None,
                "fashion_type": None,
                "animal_fortune": None,
                "insight": "ファッションタイプ診断または動物占いを実施してください。",
                "generated_at": datetime.now().isoformat()
            }

        # 最近のファッションレビュー（過去7件）を取得
        fashion_reviews = self.get_recent_fashion_reviews(user_id, limit=7)
        print(f"[UserInsight] Retrieved {len(fashion_reviews)} fashion reviews for user {user_id}")

        # Geminiプロンプト構築
        prompt = self._build_insight_prompt(fashion_type, animal_fortune, fashion_reviews)

        # Gemini APIでインサイト生成
        try:
            insight_text = self._generate_insight_with_gemini(prompt)
        except Exception as e:
            print(f"[UserInsight] Error generating insight: {e}")
            insight_text = "インサイトの生成に失敗しました。もう一度お試しください。"

        # インサイトIDを生成
        insight_id = str(uuid.uuid4())
        generated_at = datetime.now().isoformat()

        # Firestoreに保存
        try:
            insight_data = {
                "id": insight_id,
                "user_id": user_id,
                "fashion_type_code": fashion_type.get('type_code') if fashion_type else None,
                "animal_number": animal_fortune.get('animal_number') if animal_fortune else None,
                "insight": insight_text,
                "generated_at": generated_at,
                "created_at": firestore.SERVER_TIMESTAMP
            }

            doc_ref = self.db.collection('user-insights').document(insight_id)
            doc_ref.set(insight_data)

            print(f"[UserInsight] Saved insight {insight_id} for user {user_id}")

        except Exception as e:
            print(f"[UserInsight] Error saving insight to Firestore: {e}")
            # 保存に失敗してもインサイトは返す

        return {
            "status": "success",
            "user_id": user_id,
            "insight_id": insight_id,
            "fashion_type": fashion_type,
            "animal_fortune": animal_fortune,
            "insight": insight_text,
            "generated_at": generated_at
        }

    def get_insight_history(self, user_id: str, limit: int = 10) -> list:
        """
        ユーザーのインサイト履歴を取得

        Args:
            user_id: ユーザーID
            limit: 取得件数（デフォルト: 10）

        Returns:
            list: インサイト履歴（新しい順）
        """
        try:
            # user-insightsコレクションからユーザーのドキュメントを取得
            docs = (
                self.db.collection('user-insights')
                .where('user_id', '==', user_id)
                .stream()
            )

            # Pythonでソートして最新N件を取得
            all_docs = []
            for doc in docs:
                data = doc.to_dict()
                all_docs.append({
                    "insight_id": data.get('id'),
                    "user_id": data.get('user_id'),
                    "fashion_type_code": data.get('fashion_type_code'),
                    "animal_number": data.get('animal_number'),
                    "insight": data.get('insight'),
                    "generated_at": data.get('generated_at')
                })

            # generated_atでソート（降順）
            all_docs.sort(key=lambda x: x.get('generated_at', ''), reverse=True)

            return all_docs[:limit]

        except Exception as e:
            print(f"[UserInsight] Error fetching insight history: {e}")
            return []

    def get_recent_fashion_reviews(self, user_id: str, limit: int = 7) -> list:
        """
        ユーザーの最近のファッションレビュー（コーディネート）を取得

        Args:
            user_id: ユーザーID
            limit: 取得件数（デフォルト: 7）

        Returns:
            list: ファッションレビュー（新しい順）
        """
        try:
            # fashion-reviewコレクションからユーザーのドキュメントを取得
            docs = (
                self.db.collection('fashion-review')
                .where('user_id', '==', user_id)
                .stream()
            )

            # Pythonでソートして最新N件を取得
            all_docs = []
            for doc in docs:
                data = doc.to_dict()
                all_docs.append({
                    "coordinate_id": data.get('id'),
                    "date": data.get('date'),
                    "ai_catchphrase": data.get('ai_catchphrase'),
                    "ai_review_comment": data.get('ai_review_comment'),
                    "tags": data.get('tags', []),
                    "item_types": data.get('item_types', []),
                    "created_at": data.get('created_at')
                })

            # created_atでソート（降順）
            all_docs.sort(key=lambda x: x.get('created_at', ''), reverse=True)

            return all_docs[:limit]

        except Exception as e:
            print(f"[UserInsight] Error fetching fashion reviews: {e}")
            return []

    def _build_insight_prompt(self, fashion_type: Optional[Dict], animal_fortune: Optional[Dict], fashion_reviews: Optional[list] = None) -> str:
        """
        インサイト生成用プロンプトを構築

        Args:
            fashion_type: ファッションタイプ情報
            animal_fortune: 動物占い情報
            fashion_reviews: ファッションレビュー履歴（最大7件）

        Returns:
            str: Geminiプロンプト
        """
        # Load intro from file
        prompt_loader = get_prompt_loader()
        intro = prompt_loader.load("user_insight_intro")

        prompt_parts = [intro, ""]

        # ファッションタイプ情報
        if fashion_type:
            prompt_parts.append("## ファッションタイプ診断結果")
            prompt_parts.append(f"- タイプ名: {fashion_type.get('type_name')}")
            prompt_parts.append(f"- グループ: {fashion_type.get('group')} ({fashion_type.get('group_color')})")
            prompt_parts.append(f"- 特徴: {fashion_type.get('core_stance')}")
            prompt_parts.append(f"- 詳細: {fashion_type.get('description')[:150]}...")

            scores = fashion_type.get('scores', {})
            prompt_parts.append(f"- スコア:")
            prompt_parts.append(f"  - トレンド感度: {scores.get('trend_score')}/5")
            prompt_parts.append(f"  - 自己表現: {scores.get('self_score')}/5")
            prompt_parts.append(f"  - 社会調和: {scores.get('social_score')}/5")
            prompt_parts.append(f"  - 機能重視: {scores.get('function_score')}/5")
            prompt_parts.append(f"  - 投資志向: {scores.get('economy_score')}/5\n")

        # 動物占い情報
        if animal_fortune:
            prompt_parts.append("## 動物占い結果")
            prompt_parts.append(f"- 動物: {animal_fortune.get('animal_name')} ({animal_fortune.get('animal')})")

            base_personality = animal_fortune.get('base_personality')
            if base_personality:
                prompt_parts.append(f"- 基本性格: {base_personality[:150]}...")

            life_tendency = animal_fortune.get('life_tendency')
            if life_tendency:
                prompt_parts.append(f"- 人生傾向: {life_tendency[:150]}...\n")

        # ファッションレビュー履歴
        if fashion_reviews and len(fashion_reviews) > 0:
            prompt_parts.append("## 実際のコーディネート履歴")
            prompt_parts.append("ユーザーが実際に投稿したコーディネートのレビューです。")
            prompt_parts.append("**🎯 分析の優先順位:**")
            prompt_parts.append("1. **直近3件を最重要視** - ユーザーの現在のスタイル傾向を表す")
            prompt_parts.append("2. 4-7件目は参考情報 - 過去のスタイル傾向との比較に使用\n")

            # 直近3件（最重要）
            recent_3 = fashion_reviews[:3]
            if recent_3:
                prompt_parts.append("### 🔥【最重要】直近3件のコーディネート（ユーザーの現在のスタイル）")
                prompt_parts.append("**この3件から現在のスタイル傾向を必ず分析してください！**\n")

                for i, review in enumerate(recent_3, 1):
                    prompt_parts.append(f"**📅 直近コーデ {i}** ({review.get('date', '日付不明')})")
                    prompt_parts.append(f"- キャッチフレーズ: {review.get('ai_catchphrase', 'なし')}")
                    prompt_parts.append(f"- レビュー: {review.get('ai_review_comment', 'なし')[:150]}...")
                    tags = review.get('tags', [])
                    if tags:
                        prompt_parts.append(f"- タグ: {', '.join(tags[:5])}")
                    item_types = review.get('item_types', [])
                    if item_types:
                        prompt_parts.append(f"- アイテム種類: {', '.join(item_types)}")
                    prompt_parts.append("")

            # 4-7件目（参考情報）
            older_reviews = fashion_reviews[3:7]
            if older_reviews:
                prompt_parts.append("### 📚【参考】4-7件目のコーディネート（過去のスタイル傾向）")
                prompt_parts.append("**過去のスタイルとの比較・変化の検出に使用してください**\n")

                for i, review in enumerate(older_reviews, 4):
                    prompt_parts.append(f"**コーデ {i}** ({review.get('date', '日付不明')})")
                    prompt_parts.append(f"- キャッチフレーズ: {review.get('ai_catchphrase', 'なし')}")
                    tags = review.get('tags', [])
                    if tags:
                        prompt_parts.append(f"- タグ: {', '.join(tags[:3])}")
                    prompt_parts.append("")

            prompt_parts.append("")

        # Load output instructions from file
        output_instructions = prompt_loader.load("user_insight_output_instructions")
        prompt_parts.append(output_instructions)

        return "\n".join(prompt_parts)

    def _generate_insight_with_gemini(self, prompt: str) -> str:
        """
        Gemini APIでインサイトを生成

        Args:
            prompt: プロンプト

        Returns:
            str: 生成されたインサイトテキスト
        """
        from google.genai import types

        try:
            # GeminiServiceのclientを使用（既存のfashion-review実装と同じ）
            response = self.gemini_service.client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "insight": {"type": "string"}
                        },
                        "required": ["insight"]
                    },
                    temperature=0.7,
                    max_output_tokens=1000,
                    thinking_config=types.ThinkingConfig(thinking_budget=0, include_thoughts=False)
                ),
            )

            result = json.loads(response.text)
            insight_text = result.get("insight", "インサイトの生成に失敗しました。")

            print(f"[UserInsight] Gemini generated insight ({len(insight_text)} chars)")
            return insight_text

        except Exception as e:
            print(f"[UserInsight] Gemini API error: {e}")
            raise
