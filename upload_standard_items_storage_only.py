#!/usr/bin/env python3
"""
Standard Items を Firebase Storage のみにアップロード（Firestore登録はスキップ）
Firestore登録は register_standard_items_firestore.py で別途実行
"""

import os
import json
import firebase_admin
from firebase_admin import credentials, storage
from pathlib import Path
from typing import List, Dict, Any
import mimetypes
from tqdm import tqdm
import logging
from datetime import datetime

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('upload_storage_only_log.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StorageOnlyUploader:
    def __init__(self, bucket):
        """Firebase Storage アップローダーの初期化"""
        self.bucket = bucket
        self.uploaded_files = []
        self.failed_files = []

    def parse_filename(self, filename: str) -> Dict[str, str]:
        """ファイル名から情報を抽出"""
        name_without_ext = Path(filename).stem
        parts = name_without_ext.split('_')

        return {
            'main_category': parts[0] if len(parts) > 0 else 'unknown',
            'sub_category': parts[1] if len(parts) > 1 else '',
            'color': parts[2] if len(parts) > 2 else ''
        }

    def get_standard_items(self, men_dir: str, women_dir: str) -> List[Dict[str, Any]]:
        """standard-items ディレクトリから全アイテムを取得"""
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
                        'size': os.path.getsize(file_path)
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
                        'size': os.path.getsize(file_path)
                    })

        return items

    def upload_to_storage_only(self, item_info: Dict[str, Any]) -> Dict[str, Any]:
        """Storage にのみアップロード（Firestoreはスキップ）"""
        try:
            local_path = item_info['local_path']
            gender = item_info['gender']
            filename = item_info['filename']

            # Storage内のパスを生成
            storage_path = f"standard-items/{gender}/{filename}"

            # 既にアップロード済みか確認
            blob = self.bucket.blob(storage_path)
            if blob.exists():
                blob.reload()
                logger.info(f"⏭️  既存: {storage_path}")

                # 公開URLを取得
                blob.make_public()
                public_url = blob.public_url

                result = {
                    'status': 'already_exists',
                    'local_path': local_path,
                    'storage_path': storage_path,
                    'public_url': public_url,
                    'gender': gender,
                    'main_category': item_info['main_category'],
                    'sub_category': item_info['sub_category'],
                    'color': item_info['color'],
                    'filename': filename
                }

                self.uploaded_files.append(result)
                return result

            # Content-Typeを設定
            content_type = mimetypes.guess_type(local_path)[0]
            if content_type:
                blob.content_type = content_type

            # ファイルをアップロード
            blob.upload_from_filename(local_path)

            # 公開URLを生成
            blob.make_public()
            public_url = blob.public_url

            result = {
                'status': 'success',
                'local_path': local_path,
                'storage_path': storage_path,
                'public_url': public_url,
                'gender': gender,
                'main_category': item_info['main_category'],
                'sub_category': item_info['sub_category'],
                'color': item_info['color'],
                'filename': filename
            }

            self.uploaded_files.append(result)
            logger.info(f"✅ アップロード成功: {storage_path}")

            return result

        except Exception as e:
            error_result = {
                'status': 'error',
                'local_path': item_info['local_path'],
                'error': str(e)
            }

            self.failed_files.append(error_result)
            logger.error(f"❌ アップロード失敗: {item_info['local_path']} - {str(e)}")

            return error_result

    def upload_all(self, men_dir: str, women_dir: str):
        """すべてのアイテムを Storage にアップロード"""
        logger.info(f"Men's アイテム検索: {men_dir}")
        logger.info(f"Women's アイテム検索: {women_dir}")

        items = self.get_standard_items(men_dir, women_dir)
        logger.info(f"見つかったアイテム数: {len(items)}")
        logger.info(f"  Men's: {sum(1 for item in items if item['gender'] == 'men')}")
        logger.info(f"  Women's: {sum(1 for item in items if item['gender'] == 'women')}")

        # プログレスバーと共にアップロード
        for item in tqdm(items, desc="Storage アップロード中"):
            self.upload_to_storage_only(item)

        # 結果サマリー
        logger.info(f"\nStorage アップロード完了:")
        logger.info(f"成功: {len([f for f in self.uploaded_files if f['status'] == 'success'])}")
        logger.info(f"既存: {len([f for f in self.uploaded_files if f['status'] == 'already_exists'])}")
        logger.info(f"失敗: {len(self.failed_files)}")

        # 結果をJSONファイルに保存
        self.save_results()

    def save_results(self):
        """アップロード結果をJSONファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = f"upload_storage_only_results_{timestamp}.json"

        results = {
            'timestamp': timestamp,
            'summary': {
                'total_uploaded': len([f for f in self.uploaded_files if f['status'] == 'success']),
                'total_already_exists': len([f for f in self.uploaded_files if f['status'] == 'already_exists']),
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


def main():
    # 設定
    CRED_PATH = '/Users/yuki.hamada/Desktop/IRODORI/firebase/irodori-e5c71-firebase-adminsdk-fbsvc-6b9a947875.json'
    BUCKET_NAME = "irodori-e5c71.firebasestorage.app"
    MEN_DIR = "/Users/yuki.hamada/Desktop/IRODORI/data/item/standard-items/men"
    WOMEN_DIR = "/Users/yuki.hamada/Desktop/IRODORI/data/item/standard-items/women"

    logger.info("=" * 70)
    logger.info("Standard Items を Firebase Storage にアップロード（Firestore登録なし）")
    logger.info("=" * 70)

    # 認証ファイルの存在確認
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
    logger.info("\n[初期化] Firebase Storage 接続中...")
    try:
        cred = credentials.Certificate(CRED_PATH)
        firebase_admin.initialize_app(cred, {
            'storageBucket': BUCKET_NAME
        })
        bucket = storage.bucket()
        logger.info("✅ Firebase Storage 接続成功")
    except Exception as e:
        logger.error(f"❌ Firebase接続失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # アップローダーの初期化と実行
    try:
        uploader = StorageOnlyUploader(bucket)
        uploader.upload_all(MEN_DIR, WOMEN_DIR)

        logger.info("\n" + "=" * 70)
        logger.info("✅ Storage アップロード完了")
        logger.info("次のステップ: register_standard_items_firestore.py を実行してください")
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
