#!/usr/bin/env python3
"""
REST API を使って Firestore に登録（gRPCの代替）
DNS問題を回避するための別アプローチ
"""

import os
import json
import requests
from pathlib import Path
from typing import List, Dict, Any
from tqdm import tqdm
import logging
import hashlib
import firebase_admin
from firebase_admin import credentials, storage
from datetime import datetime

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('register_firestore_rest_log.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FirestoreRestRegistrar:
    def __init__(self, project_id: str, access_token: str, bucket):
        """Firestore REST API 登録処理の初期化"""
        self.project_id = project_id
        self.access_token = access_token
        self.bucket = bucket
        self.base_url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents"
        self.registered_count = 0
        self.skipped_count = 0
        self.failed_count = 0

    def parse_filename(self, filename: str) -> Dict[str, str]:
        """ファイル名から情報を抽出"""
        name_without_ext = Path(filename).stem
        parts = name_without_ext.split('_')

        return {
            'main_category': parts[0] if len(parts) > 0 else 'unknown',
            'sub_category': parts[1] if len(parts) > 1 else '',
            'color': parts[2] if len(parts) > 2 else ''
        }

    def get_storage_items(self) -> List[Dict[str, Any]]:
        """Storage から standard-items のファイルリストを取得"""
        logger.info("\n[1/3] Storage からファイルリストを取得中...")

        items = []

        # Men's items
        men_blobs = self.bucket.list_blobs(prefix='standard-items/men/')
        for blob in men_blobs:
            if blob.name.endswith('/'):
                continue

            filename = os.path.basename(blob.name)
            parsed = self.parse_filename(filename)
            blob.make_public()

            items.append({
                'filename': filename,
                'storage_path': blob.name,
                'storage_url': blob.public_url,
                'gender': 'men',
                'main_category': parsed['main_category'],
                'sub_category': parsed['sub_category'],
                'color': parsed['color'],
                'file_size': blob.size
            })

        # Women's items
        women_blobs = self.bucket.list_blobs(prefix='standard-items/women/')
        for blob in women_blobs:
            if blob.name.endswith('/'):
                continue

            filename = os.path.basename(blob.name)
            parsed = self.parse_filename(filename)
            blob.make_public()

            items.append({
                'filename': filename,
                'storage_path': blob.name,
                'storage_url': blob.public_url,
                'gender': 'women',
                'main_category': parsed['main_category'],
                'sub_category': parsed['sub_category'],
                'color': parsed['color'],
                'file_size': blob.size
            })

        logger.info(f"✅ Storage から {len(items)} 件のファイルを取得しました")
        return items

    def firestore_value(self, value: Any) -> Dict:
        """Python値をFirestore REST API形式に変換"""
        if isinstance(value, str):
            return {"stringValue": value}
        elif isinstance(value, int):
            return {"integerValue": str(value)}
        elif isinstance(value, bool):
            return {"booleanValue": value}
        elif isinstance(value, list):
            return {"arrayValue": {"values": [self.firestore_value(v) for v in value]}}
        elif isinstance(value, dict):
            return {"mapValue": {"fields": {k: self.firestore_value(v) for k, v in value.items()}}}
        elif value is None:
            return {"nullValue": None}
        else:
            return {"stringValue": str(value)}

    def check_already_registered_rest(self, storage_path: str) -> bool:
        """REST API で既に登録済みか確認"""
        try:
            # クエリURL
            query_url = f"{self.base_url}:runQuery"

            # クエリボディ
            query_body = {
                "structuredQuery": {
                    "from": [{"collectionId": "items"}],
                    "where": {
                        "fieldFilter": {
                            "field": {"fieldPath": "storage_path"},
                            "op": "EQUAL",
                            "value": {"stringValue": storage_path}
                        }
                    },
                    "limit": 1
                }
            }

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            response = requests.post(query_url, json=query_body, headers=headers, timeout=10)

            if response.status_code == 200:
                results = response.json()
                # 結果があれば既存
                return len(results) > 0 and 'document' in results[0]
            else:
                logger.warning(f"⚠️  クエリ失敗: {response.status_code}")
                return False

        except Exception as e:
            logger.warning(f"⚠️  既存チェック失敗: {e}")
            return False

    def register_to_firestore_rest(self, item_info: Dict[str, Any]) -> bool:
        """REST API で Firestore に登録"""
        try:
            # 既存チェック（スキップ可能）
            if self.check_already_registered_rest(item_info['storage_path']):
                logger.info(f"⏭️  既存: {item_info['filename']}")
                self.skipped_count += 1
                return True

            # ドキュメントデータ
            doc_data = {
                "fields": {
                    "filename": self.firestore_value(item_info['filename']),
                    "storage_path": self.firestore_value(item_info['storage_path']),
                    "storage_url": self.firestore_value(item_info['storage_url']),
                    "main_category": self.firestore_value(item_info['main_category']),
                    "sub_category": self.firestore_value(item_info['sub_category']),
                    "color": self.firestore_value(item_info['color']),
                    "gender": self.firestore_value(item_info['gender']),
                    "is_standard": self.firestore_value(True),
                    "file_size": self.firestore_value(item_info['file_size']),
                    "file_hash": self.firestore_value(hashlib.md5(item_info['storage_url'].encode()).hexdigest()),
                    "metadata": self.firestore_value({}),
                    "tags": self.firestore_value([]),
                    "is_active": self.firestore_value(True)
                }
            }

            # POSTリクエスト
            url = f"{self.base_url}/items"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            response = requests.post(url, json=doc_data, headers=headers, timeout=30)

            if response.status_code in [200, 201]:
                doc_id = response.json().get('name', '').split('/')[-1]
                logger.info(f"✅ 登録成功: {item_info['filename']} (Doc ID: {doc_id})")
                self.registered_count += 1
                return True
            else:
                logger.error(f"❌ 登録失敗: {item_info['filename']} - HTTP {response.status_code}: {response.text}")
                self.failed_count += 1
                return False

        except Exception as e:
            logger.error(f"❌ 登録失敗: {item_info['filename']} - {str(e)}")
            self.failed_count += 1
            return False

    def register_all(self):
        """すべてのアイテムを登録"""
        items = self.get_storage_items()

        if not items:
            logger.warning("⚠️  Storage にアイテムが見つかりません")
            return

        logger.info("\n[2/3] REST API で Firestore に登録中...")
        for item in tqdm(items, desc="Firestore 登録中"):
            self.register_to_firestore_rest(item)

        logger.info(f"\nFirestore 登録完了:")
        logger.info(f"新規登録: {self.registered_count}")
        logger.info(f"既存スキップ: {self.skipped_count}")
        logger.info(f"失敗: {self.failed_count}")


def get_access_token(cred_path: str) -> str:
    """Firebase認証情報からアクセストークンを取得"""
    import google.auth.transport.requests
    from google.oauth2 import service_account

    # サービスアカウント認証情報を読み込み
    credentials = service_account.Credentials.from_service_account_file(
        cred_path,
        scopes=['https://www.googleapis.com/auth/datastore']
    )

    # アクセストークンを取得
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)

    return credentials.token


def main():
    CRED_PATH = '/Users/yuki.hamada/Desktop/IRODORI/firebase/irodori-e5c71-firebase-adminsdk-fbsvc-6b9a947875.json'
    BUCKET_NAME = "irodori-e5c71.firebasestorage.app"
    PROJECT_ID = "irodori-e5c71"

    logger.info("=" * 70)
    logger.info("REST API で Firestore に登録（DNS問題回避版）")
    logger.info("=" * 70)

    if not os.path.exists(CRED_PATH):
        logger.error(f"❌ 認証情報ファイルが見つかりません: {CRED_PATH}")
        return 1

    logger.info("\n[初期化] Firebase 接続中...")
    try:
        # Storage用にFirebase初期化
        cred = credentials.Certificate(CRED_PATH)
        firebase_admin.initialize_app(cred, {'storageBucket': BUCKET_NAME})
        bucket = storage.bucket()

        # REST API用にアクセストークン取得
        access_token = get_access_token(CRED_PATH)

        logger.info("✅ Firebase 接続成功（REST API モード）")
    except Exception as e:
        logger.error(f"❌ Firebase接続失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1

    try:
        registrar = FirestoreRestRegistrar(PROJECT_ID, access_token, bucket)
        registrar.register_all()

        logger.info("\n" + "=" * 70)
        logger.info("✅ Firestore 登録完了")
        logger.info("=" * 70)
        return 0

    except Exception as e:
        logger.error(f"❌ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)
