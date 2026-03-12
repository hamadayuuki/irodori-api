#!/usr/bin/env python3
"""
動物占いデータをFirestoreに格納するバッチスクリプト

使用方法:
    python batch_save_animal_fortune.py

動作:
    - テストユーザーの動物占いを実行
    - 結果をFirestoreの animal-fortunes コレクションに保存
"""

import sys
from firebase_service import FirebaseService
from animal_fortune_service import AnimalFortuneService


def main():
    """メイン処理"""
    print("=" * 60)
    print("動物占いデータをFirestoreに格納")
    print("=" * 60)

    # Firebase初期化
    print("\n[1/4] Firebase接続を初期化中...")
    try:
        firebase_service = FirebaseService()
        animal_fortune_service = AnimalFortuneService(firebase_service.db)
        print("✅ Firebase接続成功")
    except Exception as e:
        print(f"❌ Firebase接続失敗: {e}")
        sys.exit(1)

    # テストデータ定義（様々な生年月日）
    test_cases = [
        {
            "user_id": "test-user-001",
            "year": 2000,
            "month": 1,
            "day": 1,
            "description": "2000年1月1日生まれ"
        },
        {
            "user_id": "test-user-002",
            "year": 1995,
            "month": 6,
            "day": 15,
            "description": "1995年6月15日生まれ"
        },
        {
            "user_id": "test-user-003",
            "year": 1990,
            "month": 12,
            "day": 31,
            "description": "1990年12月31日生まれ"
        },
        {
            "user_id": "test-user-004",
            "year": 1985,
            "month": 3,
            "day": 21,
            "description": "1985年3月21日生まれ"
        },
        {
            "user_id": "test-user-005",
            "year": 2010,
            "month": 7,
            "day": 7,
            "description": "2010年7月7日生まれ"
        }
    ]

    print(f"\n[2/4] テストケース数: {len(test_cases)}")

    # 各テストケースを処理
    print("\n[3/4] 占い実行 & Firestore保存中...")
    success_count = 0

    for i, test_case in enumerate(test_cases, 1):
        try:
            print(f"\n  テストケース {i}/{len(test_cases)}")
            print(f"  - ユーザーID: {test_case['user_id']}")
            print(f"  - 生年月日: {test_case['year']}/{test_case['month']}/{test_case['day']}")
            print(f"  - 説明: {test_case['description']}")

            # 占い実行
            result = animal_fortune_service.diagnose(
                test_case['user_id'],
                test_case['year'],
                test_case['month'],
                test_case['day']
            )

            print(f"  ✅ 占い完了")
            print(f"     動物: {result['animal']}")
            print(f"     キャラクター名: {result['animal_name']}")
            print(f"     占いID: {result['fortune_id']}")
            print(f"     基本性格: {result['base_personality'][:40]}...")

            success_count += 1

        except Exception as e:
            print(f"  ❌ エラー: {e}")
            import traceback
            traceback.print_exc()

    # 結果サマリー
    print("\n" + "=" * 60)
    print(f"[4/4] 完了: {success_count}/{len(test_cases)} 件成功")
    print("=" * 60)

    if success_count == len(test_cases):
        print("\n✅ すべてのデータがFirestoreに正常に保存されました")
        print(f"   コレクション: animal-fortunes")
        return 0
    else:
        print(f"\n⚠️  {len(test_cases) - success_count} 件のデータ保存に失敗しました")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
