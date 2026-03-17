"""
Standard Items Service
標準アイテムをFirestoreから取得するサービス
"""

import os
from typing import List, Dict, Optional
import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime

class StandardItemsService:
    def __init__(self):
        """Initialize Standard Items Service"""
        # Firebase初期化（すでに初期化されている場合はスキップ）
        # FirebaseService と互換性を持たせるため、両方のチェックを使用
        if not firebase_admin._apps:
            try:
                print("[StandardItemsService] Firebase not initialized, initializing now...")
                # Try to get credentials from file path
                cred_path = "/etc/secrets/irodori-e5c71-firebase-adminsdk-fbsvc-6b9a947875.json"

                if cred_path and os.path.exists(cred_path):
                    # シークレットファイルから認証情報を読み込み
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred, {
                        'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
                    })
                else:
                    # Application Default Credentials (ADC) を使用
                    firebase_admin.initialize_app(options={
                        'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
                    })

                print("[StandardItemsService] Firebase initialized successfully")

                # FirebaseService の初期化フラグも設定して互換性を保つ
                try:
                    from firebase_service import FirebaseService
                    FirebaseService._initialized = True
                    FirebaseService._db = firestore.client()
                    FirebaseService._bucket = storage.bucket()
                except Exception as sync_error:
                    print(f"[StandardItemsService] Warning: Could not sync with FirebaseService: {sync_error}")

            except Exception as e:
                print(f"[StandardItemsService] Error initializing Firebase: {e}")
                raise
        else:
            print("[StandardItemsService] Firebase already initialized, reusing existing app")

        self.db = firestore.client()

    def get_standard_items(
        self,
        gender: Optional[str] = None,
        main_category: Optional[str] = None,
        sub_category: Optional[str] = None,
        color: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        標準アイテムをFirestoreから取得

        Args:
            gender: 性別フィルタ ("men" or "women")
            main_category: メインカテゴリフィルタ (e.g., "アウター")
            sub_category: サブカテゴリフィルタ (e.g., "Gジャン")
            color: 色フィルタ (e.g., "ブラック")
            limit: 取得件数上限

        Returns:
            アイテムリスト
        """
        try:
            # ベースクエリ: is_standard=True のアイテムのみ
            query = self.db.collection('items').where(filter=FieldFilter('is_standard', '==', True))

            # フィルタを適用
            if gender:
                query = query.where(filter=FieldFilter('gender', '==', gender))

            if main_category:
                query = query.where(filter=FieldFilter('main_category', '==', main_category))

            if sub_category:
                query = query.where(filter=FieldFilter('sub_category', '==', sub_category))

            if color:
                query = query.where(filter=FieldFilter('color', '==', color))

            # 取得（limitを多めに取得してフィルタリング後に調整）
            # storage_pathフィルタで除外されるアイテムを考慮してlimitの2倍取得
            docs = query.limit(limit * 2).stream()

            items = []
            seen_urls = set()  # 重複チェック用（storage_urlベース）

            for doc in docs:
                data = doc.to_dict()

                # storage_pathで本物のスタンダードアイテムを判別
                # 本物: "standard-items/{gender}/..." で始まる
                # ユーザー登録: "items/{user_id}/..." で始まる
                storage_path = data.get('storage_path', '')
                if not storage_path.startswith('standard-items/'):
                    # ユーザーが誤って登録したアイテムをスキップ
                    print(f"[StandardItems] Skipping user-registered item: {doc.id} (path: {storage_path})")
                    continue

                # 重複チェック（storage_urlで判定）
                storage_url = data.get('storage_url', '')
                if storage_url in seen_urls:
                    print(f"[StandardItems] Skipping duplicate item: {doc.id} (url: {storage_url[:60]}...)")
                    continue

                seen_urls.add(storage_url)

                # uploaded_at を文字列に変換
                uploaded_at = data.get('uploaded_at')
                if uploaded_at:
                    uploaded_at = uploaded_at.isoformat() if hasattr(uploaded_at, 'isoformat') else str(uploaded_at)

                items.append({
                    'id': doc.id,
                    'filename': data.get('filename', ''),
                    'storage_url': storage_url,
                    'main_category': data.get('main_category', ''),
                    'sub_category': data.get('sub_category', ''),
                    'color': data.get('color', ''),
                    'gender': data.get('gender', ''),
                    'is_standard': data.get('is_standard', True),
                    'file_size': data.get('file_size', 0),
                    'uploaded_at': uploaded_at
                })

                # limitに達したら終了
                if len(items) >= limit:
                    break

            return items

        except Exception as e:
            print(f"Error getting standard items: {str(e)}")
            raise

    def get_categories(self, gender: Optional[str] = None) -> Dict:
        """
        標準アイテムのカテゴリ一覧を取得

        Args:
            gender: 性別フィルタ ("men" or "women")

        Returns:
            カテゴリ情報
        """
        try:
            # ベースクエリ
            query = self.db.collection('items').where('is_standard', '==', True)

            if gender:
                query = query.where('gender', '==', gender)

            # 全アイテムを取得してPython側で集計
            docs = query.stream()

            categories = {}
            total_count = 0
            seen_urls = set()  # 重複チェック用

            for doc in docs:
                data = doc.to_dict()

                # storage_pathで本物のスタンダードアイテムを判別
                storage_path = data.get('storage_path', '')
                if not storage_path.startswith('standard-items/'):
                    # ユーザーが誤って登録したアイテムをスキップ
                    continue

                # 重複チェック（storage_urlで判定）
                storage_url = data.get('storage_url', '')
                if storage_url in seen_urls:
                    continue
                seen_urls.add(storage_url)

                main_cat = data.get('main_category', 'unknown')
                sub_cat = data.get('sub_category', '')
                color = data.get('color', '')

                total_count += 1

                if main_cat not in categories:
                    categories[main_cat] = {
                        'count': 0,
                        'sub_categories': {},
                        'colors': set()
                    }

                categories[main_cat]['count'] += 1

                if sub_cat:
                    if sub_cat not in categories[main_cat]['sub_categories']:
                        categories[main_cat]['sub_categories'][sub_cat] = 0
                    categories[main_cat]['sub_categories'][sub_cat] += 1

                if color:
                    categories[main_cat]['colors'].add(color)

            # setをlistに変換
            for cat in categories.values():
                cat['colors'] = sorted(list(cat['colors']))

            return {
                'total_count': total_count,
                'categories': categories
            }

        except Exception as e:
            print(f"Error getting categories: {str(e)}")
            raise
