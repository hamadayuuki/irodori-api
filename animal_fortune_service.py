"""
Animal Fortune Service

動物占いロジックとFirestore連携を提供します。
"""

from datetime import datetime
from typing import Dict
import uuid
import sys
import os
from firebase_admin import firestore

# animal_fortuneモジュールをインポート
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'animal_fortune'))
from animal_fortune import animal_fortune, calculate_animal_number, load_calendar_data, load_animal_data


class AnimalFortuneService:
    """動物占いサービス"""

    def __init__(self, db):
        """
        Initialize Animal Fortune Service

        Args:
            db: Firestore client instance
        """
        self.db = db

    def diagnose(self, user_id: str, year: int, month: int, day: int) -> Dict:
        """
        動物占いの実行とFirestore保存

        Args:
            user_id: ユーザーID
            year: 生年（西暦）
            month: 生月
            day: 生日

        Returns:
            dict: 占い結果
        """
        # 動物占い実行
        result = animal_fortune(year, month, day)

        # カレンダーデータと動物データを読み込み
        calendar_data = load_calendar_data()
        animals = load_animal_data()

        # 動物番号を計算
        animal_number = calculate_animal_number(year, month, day, calendar_data)

        # 動物情報を取得
        animal_info = animals[animal_number]

        # 占いID生成
        fortune_id = str(uuid.uuid4())

        # Firestore保存用データ構造
        fortune_data = {
            "id": fortune_id,
            "user_id": user_id,
            "birth_year": year,
            "birth_month": month,
            "birth_day": day,
            "animal_number": animal_number,
            "animal": animal_info['animal'],
            "animal_name": animal_info['character'],
            "base_personality": result.base_personality,
            "life_tendency": result.life_tendency,
            "female_feature": result.female_feature,
            "male_feature": result.male_feature,
            "love_tendency": result.love_tendency,
            "link": animal_info['link'],
            "created_at": firestore.SERVER_TIMESTAMP
        }

        # Firestoreに保存 (animal-fortunes コレクション)
        try:
            doc_ref = self.db.collection('animal-fortunes').document(fortune_id)
            doc_ref.set(fortune_data)
            print(f"[AnimalFortune] Saved fortune {fortune_id} for user {user_id}: {animal_info['character']}")
        except Exception as e:
            print(f"[AnimalFortune] Error saving fortune: {e}")
            raise

        # レスポンス用データ（created_atは文字列に変換）
        response_data = {
            "fortune_id": fortune_id,
            "animal": animal_info['animal'],
            "animal_name": animal_info['character'],
            "base_personality": result.base_personality,
            "life_tendency": result.life_tendency,
            "female_feature": result.female_feature,
            "male_feature": result.male_feature,
            "love_tendency": result.love_tendency,
            "link": animal_info['link'],
            "created_at": datetime.now().isoformat()
        }

        return response_data

    def get_user_fortunes(self, user_id: str, limit: int = 10) -> list:
        """
        ユーザーの占い履歴を取得

        Args:
            user_id: ユーザーID
            limit: 取得件数上限

        Returns:
            list: 占い履歴リスト
        """
        try:
            docs = (
                self.db.collection('animal-fortunes')
                .where('user_id', '==', user_id)
                .order_by('created_at', direction=firestore.Query.DESCENDING)
                .limit(limit)
                .stream()
            )

            fortunes = []
            for doc in docs:
                data = doc.to_dict()
                if 'created_at' in data and data['created_at']:
                    data['created_at'] = data['created_at'].isoformat() if hasattr(data['created_at'], 'isoformat') else str(data['created_at'])
                fortunes.append(data)

            return fortunes
        except Exception as e:
            print(f"[AnimalFortune] Error getting user fortunes: {e}")
            return []
