#!/usr/bin/env python3
"""
動物占いマスターデータをFirestoreにインポートするバッチスクリプト

使用方法:
    python import_animal_master_data.py

動作:
    - animals.csv から60種類の動物の基本情報を読み込み
    - animal_feature.csv から各動物の詳細特徴を読み込み
    - 2つのCSVを結合してFirestoreの animal-master コレクションに保存
    - カレンダーデータ（calendar.csv）も animal-calendar コレクションに保存
"""

import sys
import csv
import os
import firebase_admin
from firebase_admin import credentials, firestore


def load_animals_csv():
    """animals.csvを読み込む"""
    animals = {}
    csv_path = os.path.join('animal_fortune', 'animals.csv')

    print(f"  📖 読み込み中: {csv_path}")
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

    print(f"  ✅ {len(animals)} 件の動物データを読み込みました")
    return animals


def load_animal_features_csv():
    """animal_feature.csvを読み込む"""
    features = {}
    csv_path = os.path.join('animal_fortune', 'animal_feature.csv')

    print(f"  📖 読み込み中: {csv_path}")
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            animal_number = int(row['id'])
            features[animal_number] = {
                'url': row['url'],
                'base_personality': row['base_personality'],
                'life_tendency': row['life_tendency'],
                'female_feature': row['female_feature'],
                'male_feature': row['male_feature'],
                'love_tendency': row['love_tendency']
            }

    print(f"  ✅ {len(features)} 件の特徴データを読み込みました")
    return features


def load_calendar_csv():
    """calendar.csvを読み込む"""
    calendar_data = {}
    csv_path = os.path.join('animal_fortune', 'calendar.csv')

    print(f"  📖 読み込み中: {csv_path}")
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # ヘッダー行をスキップ

        for row in reader:
            year = int(row[0])
            calendar_data[year] = {}
            # Firestoreの辞書キーは文字列である必要がある
            for i, month_value in enumerate(row[1:], 1):
                calendar_data[year][str(i)] = int(month_value)

    print(f"  ✅ {len(calendar_data)} 年分のカレンダーデータを読み込みました")
    return calendar_data


def import_animal_master_data(db):
    """動物マスターデータをFirestoreにインポート"""
    print("\n[1/3] CSVファイルから動物マスターデータを読み込み中...")

    # CSVデータ読み込み
    animals = load_animals_csv()
    features = load_animal_features_csv()

    # データ結合
    print("\n[2/3] データを結合してFirestoreに保存中...")
    success_count = 0

    for animal_number in range(1, 61):
        try:
            # 基本情報と特徴データを結合
            master_data = {
                **animals[animal_number],
                **features[animal_number]
            }

            # Firestoreに保存
            doc_ref = db.collection('animal-master').document(str(animal_number))
            doc_ref.set(master_data)

            # 進捗表示（10件ごと）
            if animal_number % 10 == 0:
                print(f"  ✅ {animal_number}/60 件保存完了")

            success_count += 1

        except Exception as e:
            print(f"  ❌ 動物番号 {animal_number} の保存に失敗: {e}")

    print(f"\n  ✅ 合計 {success_count}/60 件の動物マスターデータを保存しました")
    return success_count


def import_calendar_data(db):
    """カレンダーデータをFirestoreにインポート"""
    print("\n[3/3] カレンダーデータをFirestoreに保存中...")

    calendar_data = load_calendar_csv()
    success_count = 0

    for year, months in calendar_data.items():
        try:
            doc_ref = db.collection('animal-calendar').document(str(year))
            doc_ref.set({
                'year': year,
                'months': months
            })
            success_count += 1

        except Exception as e:
            print(f"  ❌ 年 {year} の保存に失敗: {e}")

    print(f"  ✅ {success_count}/{len(calendar_data)} 年分のカレンダーデータを保存しました")
    return success_count


def main():
    """メイン処理"""
    print("=" * 70)
    print("動物占いマスターデータをFirestoreにインポート")
    print("=" * 70)

    # Firebase初期化
    print("\n[初期化] Firebase接続中...")
    try:
        # Firebase認証情報
        cred_path = '/Users/yuki.hamada/Desktop/IRODORI/firebase/irodori-e5c71-firebase-adminsdk-fbsvc-6b9a947875.json'

        if not os.path.exists(cred_path):
            print(f"❌ 認証情報ファイルが見つかりません: {cred_path}")
            sys.exit(1)

        # Firebase初期化
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

    # 動物マスターデータインポート
    animal_count = import_animal_master_data(db)

    # カレンダーデータインポート
    calendar_count = import_calendar_data(db)

    # 結果サマリー
    print("\n" + "=" * 70)
    print("インポート完了")
    print("=" * 70)
    print(f"✅ 動物マスターデータ: {animal_count} 件")
    print(f"   コレクション: animal-master")
    print(f"✅ カレンダーデータ: {calendar_count} 件")
    print(f"   コレクション: animal-calendar")
    print("\n💡 これらのデータは今後、APIから直接参照できます")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
