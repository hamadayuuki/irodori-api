#!/usr/bin/env python3
"""
ファッションタイプマスターデータの検証スクリプト

使用方法:
    python3 verify_fashion_type_master.py

検証項目:
    1. fashion-type-master に16件のドキュメントが存在
    2. fashion-type-groups に4件のドキュメントが存在
    3. fashion-type-questions に10件のドキュメントが存在
    4. fashion-type-axes に4件のドキュメントが存在
    5. 各ドキュメントに必須フィールドが存在
"""

import sys
import os
import firebase_admin
from firebase_admin import credentials, firestore


def verify_collection(db, collection_name, expected_count, required_fields):
    """
    コレクションを検証

    Args:
        db: Firestore client
        collection_name: コレクション名
        expected_count: 期待されるドキュメント数
        required_fields: 必須フィールドのリスト

    Returns:
        bool: 検証成功ならTrue
    """
    print(f"\n{'='*60}")
    print(f"検証中: {collection_name}")
    print(f"{'='*60}")

    try:
        # コレクション内の全ドキュメントを取得
        docs = db.collection(collection_name).stream()
        docs_list = list(docs)

        # ドキュメント数の確認
        actual_count = len(docs_list)
        print(f"📊 ドキュメント数: {actual_count}/{expected_count}")

        if actual_count != expected_count:
            print(f"❌ エラー: 期待されるドキュメント数は{expected_count}件ですが、{actual_count}件見つかりました")
            return False

        # 各ドキュメントのフィールドを検証
        missing_fields_count = 0
        for doc in docs_list:
            data = doc.to_dict()
            missing_fields = []

            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)

            if missing_fields:
                print(f"⚠️  ドキュメント {doc.id}: 欠損フィールド {missing_fields}")
                missing_fields_count += 1
            else:
                print(f"✅ ドキュメント {doc.id}: すべてのフィールドが存在")

        if missing_fields_count > 0:
            print(f"\n❌ {missing_fields_count}件のドキュメントに欠損フィールドがあります")
            return False

        print(f"\n✅ {collection_name} の検証が成功しました")
        return True

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_query(db):
    """
    サンプルクエリのテスト

    Args:
        db: Firestore client
    """
    print(f"\n{'='*60}")
    print("サンプルクエリのテスト")
    print(f"{'='*60}")

    try:
        # タイプマスターからTPAQを取得
        print("\n[テスト1] fashion-type-master から TPAQ を取得")
        doc = db.collection('fashion-type-master').document('TPAQ').get()
        if doc.exists:
            data = doc.to_dict()
            print(f"✅ タイプコード: {data['type_code']}")
            print(f"✅ タイプ名: {data['type_name']}")
            print(f"✅ 説明: {data['description'][:50]}...")
        else:
            print("❌ ドキュメントが見つかりません")
            return False

        # グループからTPグループを取得
        print("\n[テスト2] fashion-type-groups から TP を取得")
        doc = db.collection('fashion-type-groups').document('TP').get()
        if doc.exists:
            data = doc.to_dict()
            print(f"✅ グループコード: {data['group_code']}")
            print(f"✅ グループ名: {data['group_name']}")
            print(f"✅ 色: {data['color']}")
            print(f"✅ 含まれるタイプ: {data['types']}")
        else:
            print("❌ ドキュメントが見つかりません")
            return False

        # 質問からQ1を取得
        print("\n[テスト3] fashion-type-questions から Q1 を取得")
        doc = db.collection('fashion-type-questions').document('Q1').get()
        if doc.exists:
            data = doc.to_dict()
            print(f"✅ 質問ID: {data['question_id']}")
            print(f"✅ 質問文: {data['question_text']}")
            print(f"✅ 軸: {data['axis']}")
        else:
            print("❌ ドキュメントが見つかりません")
            return False

        # 軸からaxis1を取得
        print("\n[テスト4] fashion-type-axes から axis1 を取得")
        doc = db.collection('fashion-type-axes').document('axis1').get()
        if doc.exists:
            data = doc.to_dict()
            print(f"✅ 軸ID: {data['axis_id']}")
            print(f"✅ 軸名: {data['axis_name']}")
            print(f"✅ 計算式: {data['calculation']}")
            print(f"✅ 判定ルール: {data['judgment_rule']}")
        else:
            print("❌ ドキュメントが見つかりません")
            return False

        print("\n✅ すべてのクエリテストが成功しました")
        return True

    except Exception as e:
        print(f"❌ クエリテスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """メイン処理"""
    print("=" * 70)
    print("ファッションタイプマスターデータの検証")
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

    # 検証実行
    results = []

    # fashion-type-master の検証
    results.append(verify_collection(
        db,
        'fashion-type-master',
        16,
        ['type_code', 'type_name', 'description', 'core_stance', 'group', 'group_code', 'group_color', 'axes']
    ))

    # fashion-type-groups の検証
    results.append(verify_collection(
        db,
        'fashion-type-groups',
        4,
        ['group_code', 'group_name', 'color', 'color_nuance', 'types']
    ))

    # fashion-type-questions の検証
    results.append(verify_collection(
        db,
        'fashion-type-questions',
        10,
        ['question_id', 'order', 'axis', 'axis_code', 'question_text', 'viewpoint', 'navigation']
    ))

    # fashion-type-axes の検証
    results.append(verify_collection(
        db,
        'fashion-type-axes',
        4,
        ['axis_id', 'axis_name', 'axis_code', 'positive_label', 'negative_label', 'calculation', 'judgment_rule']
    ))

    # サンプルクエリのテスト
    results.append(test_query(db))

    # 結果サマリー
    print("\n" + "=" * 70)
    print("検証結果サマリー")
    print("=" * 70)

    total_checks = len(results)
    passed_checks = sum(results)

    print(f"\n✅ 成功: {passed_checks}/{total_checks}")
    print(f"❌ 失敗: {total_checks - passed_checks}/{total_checks}")

    if all(results):
        print("\n🎉 すべての検証が成功しました！")
        print("ファッションタイプマスターデータは正常にFirestoreに保存されています。")
        return 0
    else:
        print("\n⚠️  一部の検証が失敗しました。")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
