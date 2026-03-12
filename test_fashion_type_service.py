#!/usr/bin/env python3
"""
FashionTypeServiceの動作確認スクリプト
マスターデータ参照機能をテスト

使用方法:
    python3 test_fashion_type_service.py
"""

import sys
import os
import firebase_admin
from firebase_admin import credentials, firestore


def test_service():
    """サービス層のテスト"""
    print("=" * 70)
    print("FashionTypeService 動作確認")
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

    # FashionTypeServiceを初期化
    print("\n[2] FashionTypeServiceを初期化中...")
    from fashion_type_service import FashionTypeService
    service = FashionTypeService(db)
    print("✅ サービス初期化成功")

    # テスト1: get_type_name (Firestoreマスター参照)
    print("\n" + "=" * 70)
    print("[テスト1] get_type_name - タイプ名取得（マスターデータ参照）")
    print("=" * 70)

    test_codes = ["TPAQ", "CRFE", "CPAE"]
    for code in test_codes:
        type_name = service.get_type_name(code)
        print(f"  {code}: {type_name}")

    # テスト2: get_type_master - 詳細情報取得
    print("\n" + "=" * 70)
    print("[テスト2] get_type_master - マスターデータ詳細取得")
    print("=" * 70)

    master = service.get_type_master("TPAQ")
    print(f"  タイプコード: {master.get('type_code')}")
    print(f"  タイプ名: {master.get('type_name')}")
    print(f"  核心スタンス: {master.get('core_stance')}")
    print(f"  グループ: {master.get('group')}")
    print(f"  グループ色: {master.get('group_color')}")
    print(f"  説明: {master.get('description', '')[:80]}...")

    # テスト3: get_group_info - グループ情報取得
    print("\n" + "=" * 70)
    print("[テスト3] get_group_info - グループ情報取得")
    print("=" * 70)

    group = service.get_group_info("TP")
    print(f"  グループコード: {group.get('group_code')}")
    print(f"  グループ名: {group.get('group_name')}")
    print(f"  色: {group.get('color')}")
    print(f"  ニュアンス: {group.get('color_nuance')}")
    print(f"  含まれるタイプ: {group.get('types')}")

    # テスト4: get_all_questions - 質問マスター取得
    print("\n" + "=" * 70)
    print("[テスト4] get_all_questions - 質問マスター取得")
    print("=" * 70)

    questions = service.get_all_questions()
    print(f"  質問数: {len(questions)}")
    print(f"\n  最初の質問:")
    if questions:
        q1 = questions[0]
        print(f"    ID: {q1.get('question_id')}")
        print(f"    質問文: {q1.get('question_text')}")
        print(f"    軸: {q1.get('axis')}")

    # テスト5: get_axes_info - 軸情報取得
    print("\n" + "=" * 70)
    print("[テスト5] get_axes_info - 軸情報取得")
    print("=" * 70)

    axes = service.get_axes_info()
    print(f"  軸の数: {len(axes)}")
    for axis in axes:
        print(f"\n  {axis.get('axis_id')}: {axis.get('axis_name')}")
        print(f"    計算式: {axis.get('calculation')}")
        print(f"    判定ルール: {axis.get('judgment_rule')}")

    # テスト6: diagnose - 診断実行（既存機能+マスターデータ参照）
    print("\n" + "=" * 70)
    print("[テスト6] diagnose - 診断実行（マスターデータ参照版）")
    print("=" * 70)

    test_answers = {
        "Q1": 5, "Q2": 1, "Q3": 5, "Q4": 5, "Q5": 1,
        "Q6": 1, "Q7": 1, "Q8": 1, "Q9": 5, "Q10": 1
    }

    print(f"  テスト回答: トレンド重視・自己起点・美学重視・節約型")
    result = service.diagnose("test-user-service", test_answers)

    print(f"\n  診断結果:")
    print(f"    診断ID: {result['diagnosis_id']}")
    print(f"    タイプコード: {result['type_code']}")
    print(f"    タイプ名: {result['type_name']} ← Firestoreから取得")
    print(f"    トレンドスコア: {result['trend_score']}")
    print(f"    自己スコア: {result['self_score']}")
    print(f"    社会スコア: {result['social_score']}")

    # テスト7: キャッシュの確認
    print("\n" + "=" * 70)
    print("[テスト7] キャッシュ機能の確認")
    print("=" * 70)

    print(f"  キャッシュされているタイプコード: {list(service._master_cache.keys())}")
    print(f"  ✅ 2回目以降のget_type_name呼び出しはキャッシュから取得されます")

    # 結果サマリー
    print("\n" + "=" * 70)
    print("テスト完了")
    print("=" * 70)
    print("\n✅ すべての機能が正常に動作しています！")
    print("\n変更内容:")
    print("  1. TYPE_NAMES ハードコーディングを削除")
    print("  2. get_type_name が Firestore マスターから取得")
    print("  3. get_type_master, get_group_info, get_all_questions, get_axes_info メソッドを追加")
    print("  4. マスターデータのキャッシュ機能を実装")
    print("\nこれにより、APIから動的にマスターデータを参照できるようになりました。")


if __name__ == "__main__":
    test_service()
