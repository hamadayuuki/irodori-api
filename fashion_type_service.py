"""
Fashion Type Diagnosis Service

16タイプ診断ロジックとFirestore連携を提供します。
"""

from datetime import datetime
from typing import Dict
import uuid
from firebase_admin import firestore


class FashionTypeService:
    """ファッションタイプ診断サービス"""

    # 16タイプマッピング (4文字コード -> タイプ名)
    # fashion-type.mdに基づく正式なタイプ名
    TYPE_NAMES = {
        "TPAQ": "アヴァンギャルド・スター",
        "TPAE": "トレンド・エディター",
        "TPFQ": "アクティブ・クリエイター",
        "TPFE": "スマート・フォロワー",
        "TRAQ": "ソーシャル・アイコン",
        "TRAE": "モテ・プランナー",
        "TRFQ": "エグゼクティブ・ノマド",
        "TRFE": "クリーン・スタンダード",
        "CPAQ": "オーセンティック・アーティスト",
        "CPAE": "ヴィンテージ・ミニマリスト",
        "CPFQ": "ヘビー・デューティー",
        "CPFE": "セルフ・ミニマリスト",
        "CRAQ": "ロイヤル・クラシック",
        "CRAE": "トラッド・コンサバ",
        "CRFQ": "プロフェッショナル・ギア",
        "CRFE": "エッセンシャル・ワーカー"
    }

    def __init__(self, db):
        """
        Initialize Fashion Type Service

        Args:
            db: Firestore client instance
        """
        self.db = db

    def calculate_scores(self, answers: Dict[str, int]) -> Dict[str, float]:
        """
        質問回答から各軸のスコアを計算

        Args:
            answers: 質問回答 (Q1-Q10, 各1-5)

        Returns:
            dict: {
                "trend_score": float,
                "self_score": float,
                "social_score": float,
                "function_score": float,
                "economy_score": float
            }
        """
        # 各軸のスコア計算（fashion-type.mdの仕様に基づく）
        # 第1軸: 流行スコア = (Q1 + (6 - Q2)) / 2
        trend_score = (answers["Q1"] + (6 - answers["Q2"])) / 2

        # 第2軸: 自己スコア = (Q3 + Q4) / 2
        self_score = (answers["Q3"] + answers["Q4"]) / 2

        # 第2軸: 社会スコア = (Q5 + Q6) / 2
        social_score = (answers["Q5"] + answers["Q6"]) / 2

        # 第3軸: 機能スコア = (Q7 + Q8) / 2
        function_score = (answers["Q7"] + answers["Q8"]) / 2

        # 第4軸: 経済スコア = (Q9 + (6 - Q10)) / 2
        economy_score = (answers["Q9"] + (6 - answers["Q10"])) / 2

        return {
            "trend_score": round(trend_score, 2),
            "self_score": round(self_score, 2),
            "social_score": round(social_score, 2),
            "function_score": round(function_score, 2),
            "economy_score": round(economy_score, 2)
        }

    def determine_type_code(self, scores: Dict[str, float]) -> str:
        """
        スコアから4文字タイプコードを判定

        Args:
            scores: 各軸のスコア辞書

        Returns:
            str: 4文字タイプコード (e.g., "TPAQ")
        """
        # 第1軸: 情報の鮮度 (T/C)
        # 流行スコア >= 3.0 なら T、< 3.0 なら C
        axis1 = "T" if scores["trend_score"] >= 3.0 else "C"

        # 第2軸: 思考の起点 (P/R)
        # 自己スコア >= 社会スコアなら P、社会スコア > 自己スコアなら R
        axis2 = "P" if scores["self_score"] >= scores["social_score"] else "R"

        # 第3軸: 価値の置所 (A/F)
        # 機能スコア < 3.0 なら A、>= 3.0 なら F
        axis3 = "A" if scores["function_score"] < 3.0 else "F"

        # 第4軸: 投資の姿勢 (Q/E)
        # 経済スコア >= 3.0 なら E、< 3.0 なら Q
        axis4 = "E" if scores["economy_score"] >= 3.0 else "Q"

        return f"{axis1}{axis2}{axis3}{axis4}"

    def get_type_name(self, type_code: str) -> str:
        """
        タイプコードからタイプ名を取得

        Args:
            type_code: 4文字タイプコード

        Returns:
            str: タイプ名
        """
        return self.TYPE_NAMES.get(type_code, "未定義タイプ")

    def diagnose(self, user_id: str, answers: Dict[str, int]) -> Dict:
        """
        ファッションタイプ診断の実行とFirestore保存

        Args:
            user_id: ユーザーID
            answers: 質問回答 (Q1-Q10)

        Returns:
            dict: 診断結果
        """
        # スコア計算
        scores = self.calculate_scores(answers)

        # タイプコード判定
        type_code = self.determine_type_code(scores)
        type_name = self.get_type_name(type_code)

        # 診断ID生成
        diagnosis_id = str(uuid.uuid4())

        # Firestore保存用データ構造
        diagnosis_data = {
            "id": diagnosis_id,
            "user_id": user_id,
            "type_code": type_code,
            "type_name": type_name,
            "trend_score": scores["trend_score"],
            "self_score": scores["self_score"],
            "social_score": scores["social_score"],
            "function_score": scores["function_score"],
            "economy_score": scores["economy_score"],
            "answers": answers,  # 回答データも保存（履歴分析用）
            "created_at": firestore.SERVER_TIMESTAMP
        }

        # Firestoreに保存 (fashion-types コレクション)
        try:
            doc_ref = self.db.collection('fashion-types').document(diagnosis_id)
            doc_ref.set(diagnosis_data)
            print(f"[FashionType] Saved diagnosis {diagnosis_id} for user {user_id}: {type_code} - {type_name}")
        except Exception as e:
            print(f"[FashionType] Error saving diagnosis: {e}")
            raise

        # レスポンス用データ（created_atは文字列に変換）
        response_data = {
            "diagnosis_id": diagnosis_id,
            "type_code": type_code,
            "type_name": type_name,
            "trend_score": scores["trend_score"],
            "self_score": scores["self_score"],
            "social_score": scores["social_score"],
            "function_score": scores["function_score"],
            "economy_score": scores["economy_score"],
            "created_at": datetime.now().isoformat()
        }

        return response_data

    def get_user_diagnoses(self, user_id: str, limit: int = 10) -> list:
        """
        ユーザーの診断履歴を取得

        Args:
            user_id: ユーザーID
            limit: 取得件数上限

        Returns:
            list: 診断履歴リスト
        """
        try:
            docs = (
                self.db.collection('fashion-types')
                .where('user_id', '==', user_id)
                .order_by('created_at', direction=firestore.Query.DESCENDING)
                .limit(limit)
                .stream()
            )

            diagnoses = []
            for doc in docs:
                data = doc.to_dict()
                if 'created_at' in data and data['created_at']:
                    data['created_at'] = data['created_at'].isoformat() if hasattr(data['created_at'], 'isoformat') else str(data['created_at'])
                diagnoses.append(data)

            return diagnoses
        except Exception as e:
            print(f"[FashionType] Error getting user diagnoses: {e}")
            return []
