#!/usr/bin/env python3
"""
動物占いマスターデータをFirestoreにインポートするスクリプト（修正版）
"""

import sys
import csv
import os
import firebase_admin
from firebase_admin import credentials, firestore


def main():
    """メイン処理"""
    print("=" * 70)
    print("動物占いマスターデータをFirestoreにインポート（修正版）")
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

    # animals.csv を読み込み
    print("\n[2] animals.csv を読み込み中...")
    animals = {}
    csv_path = 'animal_fortune/animals.csv'

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            animal_number = int(row['index'])
            animals[animal_number] = {
                'animal_number': animal_number,
                'animal': row['animal'],
                'animal_name': row['animal_name'],
                'link': row['link']
            }

    print(f"✅ {len(animals)} 件の動物データを読み込みました")

    # animal_feature.csv を読み込み（複数行対応）
    print("\n[3] animal_feature.csv を読み込み中...")
    features = {}
    csv_path = 'animal_fortune/animal_feature.csv'

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                animal_number = int(row['id'])
                features[animal_number] = {
                    'url': row['url'],
                    'base_personality': row['base_personality'],
                    'life_tendency': row['life_tendency'],
                    'female_feature': row['female_feature'],
                    'male_feature': row['male_feature'],
                    'love_tendency': row['love_tendency']
                }
            except Exception as e:
                print(f"  ⚠️  行の読み込みエラー（スキップ）: {e}")
                continue

    print(f"✅ {len(features)} 件の特徴データを読み込みました")

    # データを結合してFirestoreに保存
    print("\n[4] Firestoreに保存中...")
    success_count = 0
    error_count = 0

    for animal_number in range(1, 61):
        try:
            # 基本情報を取得
            if animal_number not in animals:
                print(f"  ⚠️  動物番号 {animal_number}: 基本情報が見つかりません")
                error_count += 1
                continue

            # マスターデータを構築
            master_data = {
                **animals[animal_number]
            }

            # 特徴データがあれば追加
            if animal_number in features:
                master_data.update(features[animal_number])
            else:
                print(f"  ⚠️  動物番号 {animal_number}: 特徴データが見つかりません（基本情報のみ保存）")

            # Firestoreに保存
            doc_ref = db.collection('animal-master').document(str(animal_number))
            doc_ref.set(master_data)

            success_count += 1

            # 進捗表示（10件ごと）
            if animal_number % 10 == 0:
                print(f"  ✅ {animal_number}/60 件保存完了")

        except Exception as e:
            print(f"  ❌ 動物番号 {animal_number} の保存に失敗: {e}")
            error_count += 1

    print(f"\n✅ 動物マスターデータ: {success_count}/60 件保存完了")
    print(f"❌ エラー: {error_count} 件")

    # カレンダーデータを読み込んで保存
    print("\n[5] カレンダーデータを保存中...")
    calendar_data = {}
    csv_path = 'animal_fortune/calendar.csv'

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # ヘッダー行をスキップ

        for row in reader:
            year = int(row[0])
            calendar_data[year] = {}
            # Firestoreの辞書キーは文字列である必要がある
            for i, month_value in enumerate(row[1:], 1):
                calendar_data[year][str(i)] = int(month_value)

    calendar_success = 0
    for year, months in calendar_data.items():
        try:
            doc_ref = db.collection('animal-calendar').document(str(year))
            doc_ref.set({
                'year': year,
                'months': months
            })
            calendar_success += 1
        except Exception as e:
            print(f"  ❌ 年 {year} の保存に失敗: {e}")

    print(f"✅ カレンダーデータ: {calendar_success}/105 件保存完了")

    # 結果サマリー
    print("\n" + "=" * 70)
    print("インポート完了")
    print("=" * 70)
    print(f"✅ 動物マスターデータ: {success_count} 件 (animal-master)")
    print(f"✅ カレンダーデータ: {calendar_success} 件 (animal-calendar)")
    print(f"\n📊 合計: {success_count + calendar_success} 件")
    print("\n💡 これらのデータは今後、APIから直接参照できます")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
