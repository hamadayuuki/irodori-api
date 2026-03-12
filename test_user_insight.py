#!/usr/bin/env python3
"""
User Insight API テストスクリプト

使用方法:
    python3 test_user_insight.py

動作:
    1. テストユーザーでファッションタイプ診断を実行
    2. テストユーザーで動物占いを実行
    3. ユーザーインサイトを生成
"""

import sys
import os
import firebase_admin
from firebase_admin import credentials, firestore


def test_user_insight():
    """User Insight API のテスト"""
    print("=" * 70)
    print("User Insight API テスト")
    print("=" * 70)

    # Firebase初期化
    print("\n[1] Firebase接続中...")
    try:
        cred_path = '/Users/yuki.hamada/Desktop/IRODORI/firebase/irodori-e5c71-firebase-adminsdk-fbsvc-6b9a947875.json'

        if not os.path.exists(cred_path):
            print(f"❌ 認証情報ファイルが見つかりません: {cred_path}")
            sys.exit(1)

        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {
            'storageBucket': 'irodori-e5c71.firebasestorage.app'
        })

        db = firestore.client()
        print("✅ Firebase接続成功")
    except Exception as e:
        print(f"❌ Firebase接続失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # テストユーザーID
    test_user_id = "test-user-insight-001"

    # ファッションタイプ診断を実行
    print("\n[2] ファッションタイプ診断を実行中...")
    from fashion_type_service import FashionTypeService
    fashion_service = FashionTypeService(db)

    test_answers = {
        "Q1": 5, "Q2": 1, "Q3": 5, "Q4": 5, "Q5": 1,
        "Q6": 1, "Q7": 1, "Q8": 1, "Q9": 5, "Q10": 1
    }

    fashion_result = fashion_service.diagnose(test_user_id, test_answers)
    print(f"✅ ファッションタイプ: {fashion_result['type_name']} ({fashion_result['type_code']})")

    # 動物占いを実行
    print("\n[3] 動物占いを実行中...")
    from animal_fortune_service import AnimalFortuneService
    animal_service = AnimalFortuneService(db)

    animal_result = animal_service.diagnose(test_user_id, 2000, 1, 1)
    print(f"✅ 動物: {animal_result['animal_name']} ({animal_result['animal']})")

    # ユーザーインサイトを生成
    print("\n[4] ユーザーインサイトを生成中...")
    from user_insight_service import UserInsightService
    insight_service = UserInsightService(db)

    insight_result = insight_service.generate_insight(test_user_id)

    print("\n" + "=" * 70)
    print("インサイト生成結果")
    print("=" * 70)
    print(f"ステータス: {insight_result['status']}")
    print(f"ユーザーID: {insight_result['user_id']}")

    if insight_result['fashion_type']:
        print(f"\n【ファッションタイプ】")
        print(f"  タイプ名: {insight_result['fashion_type']['type_name']}")
        print(f"  グループ: {insight_result['fashion_type']['group']} ({insight_result['fashion_type']['group_color']})")

    if insight_result['animal_fortune']:
        print(f"\n【動物占い】")
        print(f"  動物名: {insight_result['animal_fortune']['animal_name']}")
        print(f"  動物: {insight_result['animal_fortune']['animal']}")

    print(f"\n【インサイト】")
    print(f"{insight_result['insight']}")
    print(f"\n生成日時: {insight_result['generated_at']}")

    print("\n" + "=" * 70)
    print("✅ テスト完了！")
    print("=" * 70)
    print("\nAPI エンドポイント:")
    print(f"  GET /api/user-insight?userid={test_user_id}")
    print("\n次のコマンドで起動してAPIをテストできます:")
    print("  uvicorn main:app --reload")
    print("=" * 70)


if __name__ == "__main__":
    test_user_insight()
