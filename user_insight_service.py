"""
User Insight Service

ユーザーのファッションタイプと動物占い結果からインサイトを生成します。
"""

from datetime import datetime
from typing import Dict, Optional
import json
from firebase_admin import firestore
from gemini_service import GeminiService


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
        ユーザーのインサイトを生成

        Args:
            user_id: ユーザーID

        Returns:
            dict: {
                "status": str,
                "user_id": str,
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
                "fashion_type": None,
                "animal_fortune": None,
                "insight": "ファッションタイプ診断または動物占いを実施してください。",
                "generated_at": datetime.now().isoformat()
            }

        # Geminiプロンプト構築
        prompt = self._build_insight_prompt(fashion_type, animal_fortune)

        # Gemini APIでインサイト生成
        try:
            insight_text = self._generate_insight_with_gemini(prompt)
        except Exception as e:
            print(f"[UserInsight] Error generating insight: {e}")
            insight_text = "インサイトの生成に失敗しました。もう一度お試しください。"

        return {
            "status": "success",
            "user_id": user_id,
            "fashion_type": fashion_type,
            "animal_fortune": animal_fortune,
            "insight": insight_text,
            "generated_at": datetime.now().isoformat()
        }

    def _build_insight_prompt(self, fashion_type: Optional[Dict], animal_fortune: Optional[Dict]) -> str:
        """
        インサイト生成用プロンプトを構築

        Args:
            fashion_type: ファッションタイプ情報
            animal_fortune: 動物占い情報

        Returns:
            str: Geminiプロンプト
        """
        prompt_parts = [
            "あなたはプロのファッションアドバイザーです。",
            "ユーザーのファッションタイプと動物占いの結果から、ファッションに関するインサイト（洞察）を生成してください。\n"
        ]

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

        # 出力指示
        prompt_parts.append("""
## 出力指示
上記の情報を踏まえて、ユーザーのファッションに関するインサイトを生成してください。

**出力ガイドライン:**
- 200-300文字程度で簡潔にまとめる
- ファッションタイプと動物占いの両方の情報を統合して分析する
- ポジティブで親しみやすい口調で書く
- 具体的なファッションアドバイスを含める
- 可読性を高めるために適宜改行（\\n）を使用する
- 強調箇所は **太字** にする
- 箇条書きを使う場合は2番目以降の行頭に2段改行（\\n\\n）を入れる

**出力形式:**
{
    "insight": "<ユーザーのファッションインサイト（200-300文字）>"
}

**出力例:**
{
    "insight": "あなたは**最先端のトレンドを自分らしく取り入れる個性派**タイプですね！動物占いの結果から、クールでさっぱりとした性格が見えます。\\n\\n**おすすめスタイル:**\\n- デザイナーズブランドの新作を誰よりも早く着こなす\\n- 独創的なアイテムを主役にしたスタイル\\n- シンプルながらも一点豪華主義で個性を演出\\n\\nマイペースながらも、ファッションで自分を表現することを大切にしているあなたには、トレンドを意識しつつも「自分らしさ」を忘れないスタイリングがぴったりです！"
}
""")

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
