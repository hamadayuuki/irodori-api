#!/usr/bin/env python3
"""
Storage にアップロード済みの Standard Items を Firestore に登録
既存チェックなしのシンプル版（import_fashion_type_master.py と同じパターン）
"""

import os
import sys
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
        logging.FileHandler('register_simple_log.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def parse_filename(filename: str) -> Dict[str, str]:
    """ファイル名から情報を抽出"""
    name_without_ext = Path(filename).stem
    parts = name_without_ext.split('_')

    return {
        'main_category': parts[0] if len(parts) > 0 else 'unknown',
        'sub_category': parts[1] if len(parts) > 1 else '',
        'color': parts[2] if len(parts) > 2 else ''
    }


def get_storage_items(bucket) -> List[Dict[str, Any]]:
    """Storage から standard-items のファイルリストを取得"""
    logger.info("\n[1/2] Storage からファイルリストを取得中...")

    items = []

    # Men's items
    logger.info("Men's アイテムを取得中...")
    men_blobs = bucket.list_blobs(prefix='standard-items/men/')
    for blob in men_blobs:
        if blob.name.endswith('/'):
            continue

        filename = os.path.basename(blob.name)
        parsed = parse_filename(filename)
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
    logger.info("Women's アイテムを取得中...")
    women_blobs = bucket.list_blobs(prefix='standard-items/women/')
    for blob in women_blobs:
        if blob.name.endswith('/'):
            continue

        filename = os.path.basename(blob.name)
        parsed = parse_filename(filename)
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
    logger.info(f"  Men's: {sum(1 for item in items if item['gender'] == 'men')}")
    logger.info(f"  Women's: {sum(1 for item in items if item['gender'] == 'women')}")

    return items


def register_item(db, item_info: Dict[str, Any]) -> bool:
    """Firestore に登録（既存チェックなし）"""
    try:
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
            'file_hash': hashlib.md5(item_info['storage_url'].encode()).hexdigest(),
            'uploaded_at': firestore.SERVER_TIMESTAMP,
            'metadata': {},
            'tags': [],
            'is_active': True
        }

        # items コレクションに追加
        doc_ref = db.collection('items').add(doc_data)
        logger.info(f"  ✅ {item_info['filename']}")
        return True

    except Exception as e:
        logger.error(f"  ❌ {item_info['filename']} の登録に失敗: {e}")
        return False


def register_all_items(db, bucket):
    """すべてのアイテムを登録"""
    items = get_storage_items(bucket)

    if not items:
        logger.warning("⚠️  Storage にアイテムが見つかりません")
        return 0

    logger.info("\n[2/2] Firestore に登録中...")
    success_count = 0

    for item in items:
        if register_item(db, item):
            success_count += 1

    logger.info(f"\n  ✅ 合計 {success_count}/{len(items)} 件を登録しました")
    return success_count


def create_category_summary(db):
    """カテゴリ統計を作成"""
    logger.info("\n[3/3] カテゴリ統計を作成中...")
    try:
        # 標準アイテムを全取得
        docs = db.collection('items').where('is_standard', '==', True).stream()

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

        db.collection('statistics').document('standard_items_summary').set(stats_doc)
        logger.info("  ✅ 統計情報を更新しました")

    except Exception as e:
        logger.error(f"  ❌ 統計の更新エラー: {e}")


def main():
    """メイン処理"""
    logger.info("=" * 70)
    logger.info("Standard Items を Firestore に登録（シンプル版）")
    logger.info("=" * 70)

    # 設定
    cred_path = '/Users/yuki.hamada/Desktop/IRODORI/firebase/irodori-e5c71-firebase-adminsdk-fbsvc-6b9a947875.json'
    bucket_name = "irodori-e5c71.firebasestorage.app"

    # 認証ファイルの存在確認
    if not os.path.exists(cred_path):
        logger.error(f"❌ 認証情報ファイルが見つかりません: {cred_path}")
        sys.exit(1)

    # Firebase初期化
    logger.info("\n[初期化] Firebase接続中...")
    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {
            'storageBucket': bucket_name
        })

        db = firestore.client()
        bucket = storage.bucket()
        logger.info("✅ Firebase接続成功")
    except Exception as e:
        logger.error(f"❌ Firebase接続失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # データ登録
    try:
        item_count = register_all_items(db, bucket)

        # 統計作成
        if item_count > 0:
            create_category_summary(db)

        # 結果サマリー
        logger.info("\n" + "=" * 70)
        logger.info("登録完了")
        logger.info("=" * 70)
        logger.info(f"✅ アイテム: {item_count} 件 (items コレクション)")
        logger.info("\n💡 これらのデータは /api/standard-items から取得できます")
        logger.info("=" * 70)

        return 0

    except Exception as e:
        logger.error(f"❌ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
