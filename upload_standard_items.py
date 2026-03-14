#!/usr/bin/env python3
"""
Firebase Storage & Firestore アップロードスクリプト（Standard Items用）
standard-items/men/ および standard-items/women/ 内のアイテム画像を
Firebase Storageにアップロードし、Firestoreの items コレクションに保存します。

ファイル命名規則: {カテゴリ}_{サブカテゴリ}_{色}.png
例: アウター_Gジャン_インディゴ.png
"""

import os
import json
import firebase_admin
from firebase_admin import credentials, storage, firestore
from pathlib import Path
from typing import List, Dict, Any, Optional
import mimetypes
from tqdm import tqdm
import logging
from datetime import datetime
import hashlib

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('upload_standard_items_log.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class StandardItemsUploader:
    def __init__(self, db, bucket):
        """
        Firebase Storage & Firestoreアップローダーの初期化

        Args:
            db: Firestore client
            bucket: Storage bucket
        """
        self.bucket = bucket
        self.db = db
        self.uploaded_files = []
        self.failed_files = []

    def parse_filename(self, filename: str) -> Dict[str, str]:
        """
        ファイル名から情報を抽出

        Args:
            filename: ファイル名（例: アウター_Gジャン_インディゴ.png）

        Returns:
            解析結果 {main_category, sub_category, color}
        """
        # 拡張子を除去
        name_without_ext = Path(filename).stem

        # アンダースコアで分割
        parts = name_without_ext.split('_')

        return {
            'main_category': parts[0] if len(parts) > 0 else 'unknown',
            'sub_category': parts[1] if len(parts) > 1 else '',
            'color': parts[2] if len(parts) > 2 else ''
        }

    def get_standard_items(self, men_dir: str, women_dir: str) -> List[Dict[str, Any]]:
        """
        standard-items ディレクトリから全アイテムを取得

        Args:
            men_dir: men/ ディレクトリパス
            women_dir: women/ ディレクトリパス

        Returns:
            アイテム情報のリスト
        """
        items = []
        supported_formats = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}

        # Men's items
        if os.path.exists(men_dir):
            for filename in os.listdir(men_dir):
                if Path(filename).suffix.lower() in supported_formats:
                    file_path = os.path.join(men_dir, filename)
                    parsed = self.parse_filename(filename)

                    items.append({
                        'local_path': file_path,
                        'filename': filename,
                        'gender': 'men',
                        'main_category': parsed['main_category'],
                        'sub_category': parsed['sub_category'],
                        'color': parsed['color'],
                        'size': os.path.getsize(file_path),
                        'is_standard': True
                    })

        # Women's items
        if os.path.exists(women_dir):
            for filename in os.listdir(women_dir):
                if Path(filename).suffix.lower() in supported_formats:
                    file_path = os.path.join(women_dir, filename)
                    parsed = self.parse_filename(filename)

                    items.append({
                        'local_path': file_path,
                        'filename': filename,
                        'gender': 'women',
                        'main_category': parsed['main_category'],
                        'sub_category': parsed['sub_category'],
                        'color': parsed['color'],
                        'size': os.path.getsize(file_path),
                        'is_standard': True
                    })

        return items

    def generate_file_hash(self, file_path: str) -> str:
        """
        ファイルのハッシュ値を生成（重複チェック用）

        Args:
            file_path: ファイルパス

        Returns:
            MD5ハッシュ値
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def create_firestore_document(self, item_info: Dict[str, Any], storage_url: str, storage_path: str) -> Optional[str]:
        """
        Firestoreにドキュメントを作成

        Args:
            item_info: アイテム情報
            storage_url: Storage公開URL
            storage_path: Storageパス

        Returns:
            作成されたドキュメントID
        """
        try:
            from firebase_admin import firestore

            # ドキュメントデータ
            doc_data = {
                'filename': item_info['filename'],
                'storage_path': storage_path,
                'storage_url': storage_url,
                'main_category': item_info['main_category'],
                'sub_category': item_info['sub_category'],
                'color': item_info['color'],
                'gender': item_info['gender'],  # 新規フィールド
                'is_standard': True,  # 標準アイテムフラグ
                'file_size': item_info['size'],
                'file_hash': self.generate_file_hash(item_info['local_path']),
                'uploaded_at': firestore.SERVER_TIMESTAMP,
                'metadata': {},
                'tags': [],
                'is_active': True
            }

            # items コレクションに追加
            doc_ref = self.db.collection('items').add(doc_data)
            return doc_ref[1].id

        except Exception as e:
            logger.error(f"Firestoreドキュメント作成エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def upload_item(self, item_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        単一のアイテムをFirebase Storageにアップロード

        Args:
            item_info: アップロードするアイテムの情報

        Returns:
            アップロード結果
        """
        try:
            local_path = item_info['local_path']
            gender = item_info['gender']
            filename = item_info['filename']

            # Storage内のパスを生成: standard-items/men/{filename} または standard-items/women/{filename}
            storage_path = f"standard-items/{gender}/{filename}"

            # Blobを作成
            blob = self.bucket.blob(storage_path)

            # Content-Typeを設定
            content_type = mimetypes.guess_type(local_path)[0]
            if content_type:
                blob.content_type = content_type

            # ファイルをアップロード
            blob.upload_from_filename(local_path)

            # 公開URLを生成
            blob.make_public()
            public_url = blob.public_url

            # Firestoreにドキュメントを作成
            doc_id = self.create_firestore_document(item_info, public_url, storage_path)

            if doc_id:
                result = {
                    'status': 'success',
                    'local_path': local_path,
                    'storage_path': storage_path,
                    'public_url': public_url,
                    'firestore_doc_id': doc_id,
                    'gender': gender,
                    'main_category': item_info['main_category'],
                    'sub_category': item_info['sub_category'],
                    'color': item_info['color']
                }

                self.uploaded_files.append(result)
                logger.info(f"アップロード成功: {storage_path} (Doc ID: {doc_id})")
            else:
                result = {
                    'status': 'partial_success',
                    'local_path': local_path,
                    'storage_path': storage_path,
                    'public_url': public_url,
                    'error': 'Firestore document creation failed'
                }

                self.failed_files.append(result)
                logger.warning(f"部分的成功: Storageアップロード成功、Firestore登録失敗 - {storage_path}")

            return result

        except Exception as e:
            error_result = {
                'status': 'error',
                'local_path': item_info['local_path'],
                'error': str(e)
            }

            self.failed_files.append(error_result)
            logger.error(f"アップロード失敗: {item_info['local_path']} - {str(e)}")

            return error_result

    def upload_all(self, men_dir: str, women_dir: str):
        """
        すべてのアイテムをアップロード

        Args:
            men_dir: men/ ディレクトリパス
            women_dir: women/ ディレクトリパス
        """
        logger.info(f"Men's アイテム検索: {men_dir}")
        logger.info(f"Women's アイテム検索: {women_dir}")

        items = self.get_standard_items(men_dir, women_dir)
        logger.info(f"見つかったアイテム数: {len(items)}")
        logger.info(f"  Men's: {sum(1 for item in items if item['gender'] == 'men')}")
        logger.info(f"  Women's: {sum(1 for item in items if item['gender'] == 'women')}")

        # プログレスバーと共にアップロード
        for item in tqdm(items, desc="アップロード中"):
            self.upload_item(item)

        # 結果サマリー
        logger.info(f"\nアップロード完了:")
        logger.info(f"成功: {len(self.uploaded_files)}")
        logger.info(f"失敗: {len(self.failed_files)}")

        # 結果をJSONファイルに保存
        self.save_results()

    def save_results(self):
        """アップロード結果をJSONファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = f"upload_standard_items_results_{timestamp}.json"

        results = {
            'timestamp': timestamp,
            'summary': {
                'total_uploaded': len(self.uploaded_files),
                'total_failed': len(self.failed_files),
                'by_gender': {
                    'men': sum(1 for item in self.uploaded_files if item.get('gender') == 'men'),
                    'women': sum(1 for item in self.uploaded_files if item.get('gender') == 'women')
                }
            },
            'uploaded_files': self.uploaded_files,
            'failed_files': self.failed_files
        }

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info(f"結果を保存しました: {result_file}")

    def create_category_summary(self):
        """
        カテゴリごとの集計情報をFirestoreに保存
        """
        try:
            from firebase_admin import firestore

            # カテゴリ別・性別別集計
            category_stats = {}

            for file_info in self.uploaded_files:
                if file_info['status'] == 'success':
                    gender = file_info['gender']
                    main_cat = file_info['main_category']
                    sub_cat = file_info['sub_category']

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
                'total_items': len(self.uploaded_files),
                'standard_items': category_stats
            }

            self.db.collection('statistics').document('standard_items_summary').set(stats_doc)
            logger.info("標準アイテム統計情報を更新しました")

        except Exception as e:
            logger.error(f"統計の更新エラー: {str(e)}")

def main():
    # 設定
    CRED_PATH = '/Users/yuki.hamada/Desktop/IRODORI/firebase/irodori-e5c71-firebase-adminsdk-fbsvc-6b9a947875.json'
    BUCKET_NAME = "irodori-e5c71.firebasestorage.app"
    MEN_DIR = "/Users/yuki.hamada/Desktop/IRODORI/data/item/standard-items/men"
    WOMEN_DIR = "/Users/yuki.hamada/Desktop/IRODORI/data/item/standard-items/women"

    logger.info("=" * 70)
    logger.info("Standard Items を Firebase にアップロード")
    logger.info("=" * 70)

    # Firebase認証ファイルの存在確認
    if not os.path.exists(CRED_PATH):
        logger.error(f"❌ 認証情報ファイルが見つかりません: {CRED_PATH}")
        return 1

    # ディレクトリの存在確認
    if not os.path.exists(MEN_DIR):
        logger.error(f"❌ Men's ディレクトリが見つかりません: {MEN_DIR}")
        return 1

    if not os.path.exists(WOMEN_DIR):
        logger.error(f"❌ Women's ディレクトリが見つかりません: {WOMEN_DIR}")
        return 1

    # Firebase初期化
    logger.info("\n[初期化] Firebase接続中...")
    try:
        cred = credentials.Certificate(CRED_PATH)
        firebase_admin.initialize_app(cred, {
            'storageBucket': BUCKET_NAME
        })
        db = firestore.client()
        bucket = storage.bucket()
        logger.info("✅ Firebase接続成功")
    except Exception as e:
        logger.error(f"❌ Firebase接続失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # アップローダーの初期化と実行
    try:
        uploader = StandardItemsUploader(db, bucket)
        uploader.upload_all(MEN_DIR, WOMEN_DIR)

        # カテゴリ統計を作成
        uploader.create_category_summary()

        logger.info("\n" + "=" * 70)
        logger.info("✅ アップロード完了")
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
