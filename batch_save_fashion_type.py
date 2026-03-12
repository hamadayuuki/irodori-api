#!/usr/bin/env python3
"""
ファッションタイプ診断データをFirestoreに格納するバッチスクリプト

使用方法:
    python batch_save_fashion_type.py

動作:
    - テストユーザーのファッションタイプ診断を実行
    - 結果をFirestoreの fashion-types コレクションに保存
"""

import sys
from firebase_service import FirebaseService
from fashion_type_service import FashionTypeService


def main():
    """メイン処理"""
    print("=" * 60)
    print("ファッションタイプ診断データをFirestoreに格納")
    print("=" * 60)

    # Firebase初期化
    print("\n[1/4] Firebase接続を初期化中...")
    try:
        firebase_service = FirebaseService()
        fashion_type_service = FashionTypeService(firebase_service.db)
        print("✅ Firebase接続成功")
    except Exception as e:
        print(f"❌ Firebase接続失敗: {e}")
        sys.exit(1)

    # テストデータ定義
    test_cases = [
        {
            "user_id": "test-user-001",
            "description": "トレンド重視・自己起点・美学重視・節約型",
            "answers": {
                "Q1": 5, "Q2": 1, "Q3": 5, "Q4": 5, "Q5": 1,
                "Q6": 1, "Q7": 1, "Q8": 1, "Q9": 5, "Q10": 1
            }
        },
        {
            "user_id": "test-user-002",
            "description": "定番重視・社会起点・機能重視・品質投資型",
            "answers": {
                "Q1": 1, "Q2": 5, "Q3": 1, "Q4": 1, "Q5": 5,
                "Q6": 5, "Q7": 5, "Q8": 5, "Q9": 1, "Q10": 5
            }
        },
        {
            "user_id": "test-user-003",
            "description": "バランス型（中間値）",
            "answers": {
                "Q1": 3, "Q2": 3, "Q3": 3, "Q4": 3, "Q5": 3,
                "Q6": 3, "Q7": 3, "Q8": 3, "Q9": 3, "Q10": 3
            }
        }
    ]

    print(f"\n[2/4] テストケース数: {len(test_cases)}")

    # 各テストケースを処理
    print("\n[3/4] 診断実行 & Firestore保存中...")
    success_count = 0

    for i, test_case in enumerate(test_cases, 1):
        try:
            print(f"\n  テストケース {i}/{len(test_cases)}")
            print(f"  - ユーザーID: {test_case['user_id']}")
            print(f"  - 説明: {test_case['description']}")

            # 診断実行
            result = fashion_type_service.diagnose(
                test_case['user_id'],
                test_case['answers']
            )

            print(f"  ✅ 診断完了")
            print(f"     タイプコード: {result['type_code']}")
            print(f"     タイプ名: {result['type_name']}")
            print(f"     診断ID: {result['diagnosis_id']}")

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
        print(f"   コレクション: fashion-types")
        return 0
    else:
        print(f"\n⚠️  {len(test_cases) - success_count} 件のデータ保存に失敗しました")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
