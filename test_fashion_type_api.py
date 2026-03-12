#!/usr/bin/env python3
"""
ファッションタイプAPIのテストスクリプト

使用方法:
    # APIサーバーを起動してから実行
    python3 test_fashion_type_api.py
"""

import requests
import json


BASE_URL = "http://localhost:8000"


def test_get_questions():
    """質問マスターデータ取得のテスト"""
    print("\n" + "=" * 60)
    print("テスト: GET /api/fashion-type/questions")
    print("=" * 60)

    url = f"{BASE_URL}/api/fashion-type/questions"
    response = requests.get(url)

    print(f"ステータスコード: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 成功: {data['count']}件の質問を取得")
        print(f"\n最初の質問:")
        if data['questions']:
            q1 = data['questions'][0]
            print(f"  ID: {q1['question_id']}")
            print(f"  質問文: {q1['question_text']}")
            print(f"  軸: {q1['axis']}")
    else:
        print(f"❌ 失敗: {response.text}")


def test_get_type_master():
    """タイプマスター取得のテスト"""
    print("\n" + "=" * 60)
    print("テスト: GET /api/fashion-type/master/TPAQ")
    print("=" * 60)

    url = f"{BASE_URL}/api/fashion-type/master/TPAQ"
    response = requests.get(url)

    print(f"ステータスコード: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 成功: タイプ情報を取得")
        print(f"\nタイプコード: {data['type_code']}")
        print(f"タイプ名: {data['data']['type_name']}")
        print(f"核心スタンス: {data['data']['core_stance']}")
        print(f"グループ: {data['data']['group']}")
        print(f"グループ色: {data['data']['group_color']}")
        print(f"説明: {data['data']['description'][:50]}...")
    else:
        print(f"❌ 失敗: {response.text}")


def test_get_group():
    """グループ情報取得のテスト"""
    print("\n" + "=" * 60)
    print("テスト: GET /api/fashion-type/groups/TP")
    print("=" * 60)

    url = f"{BASE_URL}/api/fashion-type/groups/TP"
    response = requests.get(url)

    print(f"ステータスコード: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 成功: グループ情報を取得")
        print(f"\nグループコード: {data['group_code']}")
        print(f"グループ名: {data['data']['group_name']}")
        print(f"色: {data['data']['color']}")
        print(f"ニュアンス: {data['data']['color_nuance']}")
        print(f"含まれるタイプ: {data['data']['types']}")
    else:
        print(f"❌ 失敗: {response.text}")


def test_get_axes():
    """軸情報取得のテスト"""
    print("\n" + "=" * 60)
    print("テスト: GET /api/fashion-type/axes")
    print("=" * 60)

    url = f"{BASE_URL}/api/fashion-type/axes"
    response = requests.get(url)

    print(f"ステータスコード: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 成功: {data['count']}件の軸情報を取得")
        print(f"\n軸情報:")
        for axis in data['axes']:
            print(f"  {axis['axis_id']}: {axis['axis_name']}")
            print(f"    計算式: {axis['calculation']}")
            print(f"    判定ルール: {axis['judgment_rule']}")
    else:
        print(f"❌ 失敗: {response.text}")


def test_diagnose():
    """診断エンドポイントのテスト（既存機能の動作確認）"""
    print("\n" + "=" * 60)
    print("テスト: POST /api/fashion-type (診断)")
    print("=" * 60)

    url = f"{BASE_URL}/api/fashion-type"

    # サンプル回答データ
    payload = {
        "user_id": "test-user-api",
        "Q1": 5, "Q2": 1, "Q3": 5, "Q4": 5, "Q5": 1,
        "Q6": 1, "Q7": 1, "Q8": 1, "Q9": 5, "Q10": 1
    }

    response = requests.post(url, json=payload)

    print(f"ステータスコード: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 成功: 診断が完了")
        print(f"\n診断ID: {data['diagnosis_id']}")
        print(f"タイプコード: {data['type_code']}")
        print(f"タイプ名: {data['type_name']}")
        print(f"トレンドスコア: {data['trend_score']}")
        print(f"自己スコア: {data['self_score']}")
        print(f"社会スコア: {data['social_score']}")
    else:
        print(f"❌ 失敗: {response.text}")


def main():
    """メイン処理"""
    print("=" * 60)
    print("ファッションタイプAPI テスト")
    print("=" * 60)
    print(f"ベースURL: {BASE_URL}")

    try:
        # 各エンドポイントをテスト
        test_get_questions()
        test_get_type_master()
        test_get_group()
        test_get_axes()
        test_diagnose()

        print("\n" + "=" * 60)
        print("すべてのテストが完了しました")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("\n❌ エラー: APIサーバーに接続できません")
        print("先にAPIサーバーを起動してください: uvicorn main:app --reload")
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
