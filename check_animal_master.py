#!/usr/bin/env python3
"""
動物占いマスターデータがFirestoreに存在するか確認
"""

import os
import firebase_admin
from firebase_admin import credentials, firestore

# Firebase初期化
cred_path = '/Users/yuki.hamada/Desktop/IRODORI/firebase/irodori-e5c71-firebase-adminsdk-fbsvc-6b9a947875.json'
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred, {
    'storageBucket': 'irodori-e5c71.firebasestorage.app'
})

db = firestore.client()

print("=" * 60)
print("動物占いマスターデータの確認")
print("=" * 60)

# animal-master の確認
print("\n[1] animal-master コレクションを確認中...")
animal_docs = list(db.collection('animal-master').limit(5).stream())
print(f"  ドキュメント数（最初の5件）: {len(animal_docs)}")

if animal_docs:
    print("  ✅ animal-master は既に存在します")
    print(f"\n  サンプル（最初のドキュメント）:")
    sample = animal_docs[0].to_dict()
    print(f"    ID: {animal_docs[0].id}")
    print(f"    動物: {sample.get('animal')}")
    print(f"    キャラクター名: {sample.get('animal_name')}")
else:
    print("  ❌ animal-master は空です")

# animal-calendar の確認
print("\n[2] animal-calendar コレクションを確認中...")
calendar_docs = list(db.collection('animal-calendar').limit(5).stream())
print(f"  ドキュメント数（最初の5件）: {len(calendar_docs)}")

if calendar_docs:
    print("  ✅ animal-calendar は既に存在します")
    print(f"\n  サンプル（最初のドキュメント）:")
    sample = calendar_docs[0].to_dict()
    print(f"    年: {sample.get('year')}")
    print(f"    月データ数: {len(sample.get('months', {}))}")
else:
    print("  ❌ animal-calendar は空です")

print("\n" + "=" * 60)

if animal_docs and calendar_docs:
    print("結論: 動物占いマスターデータは既にFirestoreに格納されています")
else:
    print("結論: 動物占いマスターデータを格納する必要があります")
    print("\n実行コマンド:")
    print("  python3 import_animal_master_data.py")

print("=" * 60)
