#!/usr/bin/env python3
"""
Storage にアップロード済みの Standard Items を Firestore に登録
事前に upload_standard_items_storage_only.py を実行しておく必要があります
"""

import os
import firebase_admin
from firebase_admin import credentials, storage, firestore
from pathlib import Path
from typing import List, Dict, Any
from tqdm import tqdm
import logging
import hashlib

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('register_firestore_log.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FirestoreRegistrar:
    def __init__(self, db, bucket):
        """Firestore 登録処理の初期化"""
        self.db = db
        self.bucket = bucket
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
        logger.info("\n[1/2] Storage からファイルリストを取得中...")

        items = []

        # Men's items
        men_blobs = self.bucket.list_blobs(prefix='standard-items/men/')
        for blob in men_blobs:
            # ディレクトリをスキップ
            if blob.name.endswith('/'):
                continue

            filename = os.path.basename(blob.name)
            parsed = self.parse_filename(filename)

            # 公開URLを取得
            blob.make_public()

            items.append({
                'filename': filename,
                'storage_path': blob.name,
                'storage_url': blob.public_url,
                'gender': 'men',
                'main_category': parsed['main_category'],
                'sub_category': parsed['sub_category'],
                'color': parsed['color'],
                'file_size': blob.size,
                'content_type': blob.content_type
            })

        # Women's items
        women_blobs = self.bucket.list_blobs(prefix='standard-items/women/')
        for blob in women_blobs:
            # ディレクトリをスキップ
            if blob.name.endswith('/'):
                continue

            filename = os.path.basename(blob.name)
            parsed = self.parse_filename(filename)

            # 公開URLを取得
            blob.make_public()

            items.append({
                'filename': filename,
                'storage_path': blob.name,
                'storage_url': blob.public_url,
                'gender': 'women',
                'main_category': parsed['main_category'],
                'sub_category': parsed['sub_category'],
                'color': parsed['color'],
                'file_size': blob.size,
                'content_type': blob.content_type
            })

        logger.info(f"✅ Storage から {len(items)} 件のファイルを取得しました")
        logger.info(f"  Men's: {sum(1 for item in items if item['gender'] == 'men')}")
        logger.info(f"  Women's: {sum(1 for item in items if item['gender'] == 'women')}")

        return items

    def generate_file_hash(self, storage_url: str) -> str:
        """URLからハッシュを生成（簡易版）"""
        return hashlib.md5(storage_url.encode()).hexdigest()

    def check_already_registered(self, storage_path: str) -> bool:
        """既に登録済みか確認"""
        docs = self.db.collection('items').where('storage_path', '==', storage_path).limit(1).stream()
        return any(True for _ in docs)

    def register_to_firestore(self, item_info: Dict[str, Any]) -> bool:
        """Firestore に登録"""
        try:
            # 既に登録済みか確認
            if self.check_already_registered(item_info['storage_path']):
                logger.info(f"⏭️  既存: {item_info['filename']}")
                self.skipped_count += 1
                return True

            # ドキュメントデータ
            doc_data = {
                'filename': item_info['filename'],
                'storage_path': item_info['storage_path'],
                'storage_url': item_info['storage_url'],
                'main_category': item_info['main_category'],
                'sub_category': item_info['sub_category'],
                'color': item_info['color'],
                'gender': item_info['gender'],
                'is_standard': True,
                'file_size': item_info['file_size'],
                'file_hash': self.generate_file_hash(item_info['storage_url']),
                'uploaded_at': firestore.SERVER_TIMESTAMP,
                'metadata': {},
                'tags': [],
                'is_active': True
            }

            # items コレクションに追加
            doc_ref = self.db.collection('items').add(doc_data)
            logger.info(f"✅ 登録成功: {item_info['filename']} (Doc ID: {doc_ref[1].id})")
            self.registered_count += 1
            return True

        except Exception as e:
            logger.error(f"❌ 登録失敗: {item_info['filename']} - {str(e)}")
            self.failed_count += 1
            return False

    def register_all(self):
        """Storage の全アイテムを Firestore に登録"""
        # Storage からファイルリスト取得
        items = self.get_storage_items()

        if not items:
            logger.warning("⚠️  Storage にアイテムが見つかりません")
            return

        # Firestore に登録
        logger.info("\n[2/2] Firestore に登録中...")
        for item in tqdm(items, desc="Firestore 登録中"):
            self.register_to_firestore(item)

        # 結果サマリー
        logger.info(f"\nFirestore 登録完了:")
        logger.info(f"新規登録: {self.registered_count}")
        logger.info(f"既存スキップ: {self.skipped_count}")
        logger.info(f"失敗: {self.failed_count}")

    def create_category_summary(self):
        """カテゴリ統計を作成"""
        logger.info("\n[3/3] カテゴリ統計を作成中...")
        try:
            # 標準アイテムを全取得
            docs = self.db.collection('items').where('is_standard', '==', True).stream()

            category_stats = {}
            total_count = 0

            for doc in docs:
                data = doc.to_dict()
                gender = data.get('gender', 'unknown')
                main_cat = data.get('main_category', 'unknown')
                sub_cat = data.get('sub_category', '')

                total_count += 1

                if gender not in category_stats:
                    category_stats[gender] = {}

                if main_cat not in category_stats[gender]:
                    category_stats[gender][main_cat] = {
                        'total_items': 0,
                        'sub_categories': {}
                    }

                category_stats[gender][main_cat]['total_items'] += 1

                if sub_cat:
                    if sub_cat not in category_stats[gender][main_cat]['sub_categories']:
                        category_stats[gender][main_cat]['sub_categories'][sub_cat] = 0
                    category_stats[gender][main_cat]['sub_categories'][sub_cat] += 1

            # Firestoreに保存
            stats_doc = {
                'updated_at': firestore.SERVER_TIMESTAMP,
                'total_items': total_count,
                'standard_items': category_stats
            }

            self.db.collection('statistics').document('standard_items_summary').set(stats_doc)
            logger.info("✅ 統計情報を更新しました")

        except Exception as e:
            logger.error(f"❌ 統計の更新エラー: {str(e)}")


def main():
    # 設定
    CRED_PATH = '/Users/yuki.hamada/Desktop/IRODORI/firebase/irodori-e5c71-firebase-adminsdk-fbsvc-6b9a947875.json'
    BUCKET_NAME = "irodori-e5c71.firebasestorage.app"

    logger.info("=" * 70)
    logger.info("Storage のアイテムを Firestore に登録")
    logger.info("=" * 70)

    # 認証ファイルの存在確認
    if not os.path.exists(CRED_PATH):
        logger.error(f"❌ 認証情報ファイルが見つかりません: {CRED_PATH}")
        return 1

    # Firebase初期化
    logger.info("\n[初期化] Firebase 接続中...")
    try:
        cred = credentials.Certificate(CRED_PATH)
        firebase_admin.initialize_app(cred, {
            'storageBucket': BUCKET_NAME
        })
        db = firestore.client()
        bucket = storage.bucket()
        logger.info("✅ Firebase 接続成功")
    except Exception as e:
        logger.error(f"❌ Firebase接続失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 登録処理の実行
    try:
        registrar = FirestoreRegistrar(db, bucket)
        registrar.register_all()
        registrar.create_category_summary()

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
