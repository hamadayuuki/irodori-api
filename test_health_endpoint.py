#!/usr/bin/env python3
"""
Health Endpoint テストスクリプト（簡易版）

使用方法:
    python3 test_health_endpoint.py
"""

import sys
import os
import firebase_admin
from firebase_admin import credentials, firestore


def test_health_user_insight():
    """User Insight Health Endpoint の動作をシミュレート"""
    print("=" * 70)
    print("User Insight Health Endpoint テスト")
    print("=" * 70)

    # Firebase初期化
    print("\n[初期化] Firebase接続中...")
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

    test_user_id = "test-user-health-insight"

    print("\n=== Health check for user-insight ===")
    print(f"Test user ID: {test_user_id}")

    # Step 1: Create fashion type diagnosis
    print("\n[1/3] Creating fashion type diagnosis...")
    from fashion_type_service import FashionTypeService
    fashion_service = FashionTypeService(db)

    test_answers = {
        "Q1": 5, "Q2": 1, "Q3": 5, "Q4": 5, "Q5": 1,
        "Q6": 1, "Q7": 1, "Q8": 1, "Q9": 5, "Q10": 1
    }

    fashion_result = fashion_service.diagnose(test_user_id, test_answers)
    print(f"  ✅ Fashion type: {fashion_result['type_name']} ({fashion_result['type_code']})")

    # Step 2: Create animal fortune diagnosis
    print("\n[2/3] Creating animal fortune diagnosis...")
    from animal_fortune_service import AnimalFortuneService
    animal_service = AnimalFortuneService(db)

    animal_result = animal_service.diagnose(test_user_id, 2000, 1, 1)
    print(f"  ✅ Animal: {animal_result['animal_name']} ({animal_result['animal']})")

    # Step 3: Generate user insight
    print("\n[3/3] Generating user insight...")
    from user_insight_service import UserInsightService
    insight_service = UserInsightService(db)

    insight_result = insight_service.generate_insight(test_user_id)

    print(f"\n[Health Check] User insight generation completed")
    print(f"  - Status: {insight_result['status']}")
    print(f"  - Fashion Type: {insight_result.get('fashion_type', {}).get('type_name', 'N/A')}")
    print(f"  - Animal: {insight_result.get('animal_fortune', {}).get('animal_name', 'N/A')}")

    # Handle Gemini API error gracefully
    insight_text = insight_result.get('insight', '')
    if "失敗" in insight_text or "エラー" in insight_text:
        print(f"  - Insight: ⚠️  {insight_text}")
        print(f"\n⚠️  Note: Gemini API may not be available in local environment")
        print(f"    This is expected and will work on deployed environment with GOOGLE_GENAI_API_KEY")
    else:
        print(f"  - Insight: {insight_text[:100]}...")
        print(f"\n    Full insight:")
        print(f"    {insight_text}")

    print("\n=== User insight check completed ===")
    print("✅ Fashion type diagnosis")
    print("✅ Animal fortune diagnosis")
    print("✅ Data retrieval from Firestore")
    if "失敗" not in insight_text and "エラー" not in insight_text:
        print("✅ Gemini insight generation")
    else:
        print("⚠️  Gemini insight generation (API key required)")

    print("\n" + "=" * 70)
    print("Health Endpoint Response:")
    print("=" * 70)

    response = {
        "status": "success",
        "message": "user-insight endpoint test completed",
        "test_params": {
            "user_id": test_user_id
        },
        "result": {
            "status": insight_result['status'],
            "user_id": insight_result['user_id'],
            "fashion_type": insight_result.get('fashion_type'),
            "animal_fortune": insight_result.get('animal_fortune'),
            "insight": insight_result.get('insight'),
            "generated_at": insight_result.get('generated_at'),
            "gemini_available": "失敗" not in insight_text and "エラー" not in insight_text
        }
    }

    import json
    print(json.dumps(response, ensure_ascii=False, indent=2))

    print("\n" + "=" * 70)
    print("✅ テスト完了！")
    print("=" * 70)
    print("\nAPI エンドポイント:")
    print("  GET /health/user-insight")
    print("\n次のコマンドで起動してAPIをテストできます:")
    print("  uvicorn main:app --reload")
    print("  curl http://localhost:8000/health/user-insight")
    print("=" * 70)


if __name__ == "__main__":
    test_health_user_insight()
