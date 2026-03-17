"""
Cleanup Duplicate Standard Items in Firestore

このスクリプトはFirestoreから重複したスタンダードアイテムを削除します。
重複は storage_url で判定され、最も古いドキュメント（uploaded_at）を残し、残りを削除します。

使用方法:
    # Dry-run（削除せずに確認のみ）
    python cleanup_duplicate_items.py --dry-run

    # 実際に削除を実行
    python cleanup_duplicate_items.py --execute

    # 特定の性別のみ処理
    python cleanup_duplicate_items.py --execute --gender men
"""

import argparse
import sys
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Tuple
from standard_items_service import StandardItemsService
from firebase_admin import firestore


class DuplicateItemsCleaner:
    def __init__(self, dry_run: bool = True, gender_filter: str = None):
        """
        Initialize cleaner

        Args:
            dry_run: Trueの場合は削除せず、レポートのみ表示
            gender_filter: 性別フィルタ（"men", "women", None=全て）
        """
        self.dry_run = dry_run
        self.gender_filter = gender_filter
        self.service = StandardItemsService()
        self.db = self.service.db

    def find_duplicates(self) -> Dict[str, List[Dict]]:
        """
        重複アイテムを検出

        Returns:
            Dict[storage_url, List[item_data]]: storage_urlごとのアイテムリスト
        """
        print("=" * 80)
        print("Step 1: 重複アイテムの検出")
        print("=" * 80)

        # 全スタンダードアイテムを取得（フィルタなし、limitを大きく）
        query = self.db.collection('items').where(
            filter=firestore.FieldFilter('is_standard', '==', True)
        )

        if self.gender_filter:
            query = query.where(
                filter=firestore.FieldFilter('gender', '==', self.gender_filter)
            )

        print(f"Firestoreから取得中... (gender={self.gender_filter or 'all'})")
        docs = query.stream()

        # storage_urlごとにグループ化
        url_groups = defaultdict(list)
        total_items = 0
        skipped_user_items = 0

        for doc in docs:
            data = doc.to_dict()
            total_items += 1

            # storage_pathチェック（スタンダードアイテムのみ）
            storage_path = data.get('storage_path', '')
            if not storage_path.startswith('standard-items/'):
                skipped_user_items += 1
                continue

            storage_url = data.get('storage_url', '')
            if not storage_url:
                continue

            url_groups[storage_url].append({
                'id': doc.id,
                'data': data,
                'uploaded_at': data.get('uploaded_at'),
                'filename': data.get('filename', ''),
                'gender': data.get('gender', ''),
                'main_category': data.get('main_category', ''),
                'sub_category': data.get('sub_category', ''),
                'color': data.get('color', '')
            })

        print(f"\n取得結果:")
        print(f"  - 総アイテム数（is_standard=True）: {total_items}")
        print(f"  - ユーザー登録アイテム（除外）: {skipped_user_items}")
        print(f"  - 有効なスタンダードアイテム: {total_items - skipped_user_items}")
        print(f"  - ユニークなstorage_url数: {len(url_groups)}")

        # 重複のみ抽出
        duplicates = {url: items for url, items in url_groups.items() if len(items) > 1}

        print(f"  - 重複しているstorage_url数: {len(duplicates)}")

        return duplicates

    def analyze_duplicates(self, duplicates: Dict[str, List[Dict]]) -> Tuple[int, int]:
        """
        重複の詳細を分析して表示

        Returns:
            (total_duplicate_count, items_to_delete_count)
        """
        print("\n" + "=" * 80)
        print("Step 2: 重複の詳細分析")
        print("=" * 80)

        total_duplicate_items = 0
        items_to_delete = 0

        if not duplicates:
            print("\n✅ 重複アイテムは見つかりませんでした！")
            return 0, 0

        print(f"\n重複が見つかりました: {len(duplicates)} 種類")

        # カテゴリごとの重複数をカウント
        category_counts = defaultdict(int)

        for url, items in duplicates.items():
            total_duplicate_items += len(items)
            items_to_delete += len(items) - 1  # 1つ残すので -1

            # カテゴリ集計
            if items:
                category = f"{items[0]['gender']}/{items[0]['main_category']}/{items[0]['sub_category']}"
                category_counts[category] += len(items) - 1

        print(f"\n統計:")
        print(f"  - 重複しているアイテムの総数: {total_duplicate_items}")
        print(f"  - 削除対象のアイテム数: {items_to_delete}")
        print(f"  - 残すアイテム数: {len(duplicates)}")

        print(f"\nカテゴリ別削除数（上位10件）:")
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  - {category}: {count}件削除")

        # 詳細表示（最初の5件）
        print(f"\n重複の例（最初の5件）:")
        for i, (url, items) in enumerate(list(duplicates.items())[:5], 1):
            print(f"\n{i}. URL: {url[:70]}...")
            print(f"   重複数: {len(items)}件")
            print(f"   カテゴリ: {items[0]['gender']}/{items[0]['main_category']}/{items[0]['sub_category']}/{items[0]['color']}")
            print(f"   ドキュメントID:")
            for item in items:
                uploaded = item['uploaded_at']
                if hasattr(uploaded, 'isoformat'):
                    uploaded_str = uploaded.isoformat()
                else:
                    uploaded_str = str(uploaded)
                print(f"     - {item['id']} (uploaded: {uploaded_str})")

        return total_duplicate_items, items_to_delete

    def select_items_to_keep_and_delete(self, duplicates: Dict[str, List[Dict]]) -> Tuple[List[str], List[str]]:
        """
        残すアイテムと削除するアイテムを選択

        戦略: 最も古い uploaded_at のアイテムを残す（最初に登録されたもの）

        Returns:
            (items_to_keep, items_to_delete)
        """
        items_to_keep = []
        items_to_delete = []

        for url, items in duplicates.items():
            # uploaded_at でソート（古い順）
            sorted_items = sorted(
                items,
                key=lambda x: x['uploaded_at'] if x['uploaded_at'] else datetime.min
            )

            # 最初（最も古い）を残す
            keep_item = sorted_items[0]
            delete_items = sorted_items[1:]

            items_to_keep.append(keep_item['id'])
            items_to_delete.extend([item['id'] for item in delete_items])

        return items_to_keep, items_to_delete

    def delete_items(self, item_ids: List[str]) -> int:
        """
        指定されたアイテムをFirestoreから削除

        Args:
            item_ids: 削除するドキュメントIDのリスト

        Returns:
            削除した件数
        """
        if self.dry_run:
            print("\n⚠️  DRY-RUNモード: 実際には削除されません")
            return 0

        print("\n" + "=" * 80)
        print("Step 3: アイテムの削除")
        print("=" * 80)

        deleted_count = 0
        batch_size = 500  # Firestoreのバッチ制限

        for i in range(0, len(item_ids), batch_size):
            batch = self.db.batch()
            batch_ids = item_ids[i:i + batch_size]

            for item_id in batch_ids:
                doc_ref = self.db.collection('items').document(item_id)
                batch.delete(doc_ref)

            try:
                batch.commit()
                deleted_count += len(batch_ids)
                print(f"削除完了: {deleted_count}/{len(item_ids)} 件")
            except Exception as e:
                print(f"❌ バッチ削除エラー: {e}")
                break

        return deleted_count

    def run(self):
        """クリーンアップ処理を実行"""
        print("\n" + "=" * 80)
        print("🧹 Firestore スタンダードアイテム重複削除ツール")
        print("=" * 80)
        print(f"モード: {'🔍 DRY-RUN（削除なし）' if self.dry_run else '⚠️  実行モード（削除あり）'}")
        print(f"フィルタ: gender={self.gender_filter or 'all'}")
        print("=" * 80)

        # Step 1: 重複検出
        duplicates = self.find_duplicates()

        if not duplicates:
            print("\n✅ 処理完了: 重複アイテムは見つかりませんでした。")
            return

        # Step 2: 分析
        total_dup, to_delete_count = self.analyze_duplicates(duplicates)

        # Step 3: 削除対象を選択
        items_to_keep, items_to_delete = self.select_items_to_keep_and_delete(duplicates)

        print("\n" + "=" * 80)
        print("削除計画:")
        print("=" * 80)
        print(f"  - 残すアイテム: {len(items_to_keep)} 件")
        print(f"  - 削除するアイテム: {len(items_to_delete)} 件")

        if self.dry_run:
            print("\n" + "=" * 80)
            print("⚠️  これはDRY-RUNです。実際には何も削除されません。")
            print("実際に削除するには、以下のコマンドを実行してください:")
            print("  python cleanup_duplicate_items.py --execute")
            if self.gender_filter:
                print(f"  python cleanup_duplicate_items.py --execute --gender {self.gender_filter}")
            print("=" * 80)
            return

        # 実行モード: 確認プロンプト
        print("\n" + "=" * 80)
        print("⚠️  警告: この操作は取り消せません！")
        print("=" * 80)
        response = input(f"\n本当に {len(items_to_delete)} 件のアイテムを削除しますか？ (yes/no): ")

        if response.lower() != 'yes':
            print("\n❌ キャンセルされました。")
            return

        # Step 4: 削除実行
        deleted = self.delete_items(items_to_delete)

        print("\n" + "=" * 80)
        print("✅ 処理完了")
        print("=" * 80)
        print(f"削除されたアイテム: {deleted} 件")
        print(f"残っているアイテム: {len(items_to_keep)} 件")


def main():
    parser = argparse.ArgumentParser(
        description="Firestore スタンダードアイテムの重複削除ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # Dry-run（削除せずに確認のみ）
  python cleanup_duplicate_items.py --dry-run

  # 実際に削除を実行
  python cleanup_duplicate_items.py --execute

  # 特定の性別のみ処理
  python cleanup_duplicate_items.py --execute --gender men

注意:
  - デフォルトはdry-runモードです
  - 実行前に必ずFirestoreのバックアップを取ってください
  - 削除は取り消せません
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--dry-run',
        action='store_true',
        help='削除せずに、削除対象の確認のみ実行（推奨）'
    )
    group.add_argument(
        '--execute',
        action='store_true',
        help='実際に削除を実行（警告: 取り消せません）'
    )

    parser.add_argument(
        '--gender',
        type=str,
        choices=['men', 'women'],
        help='性別フィルタ（指定しない場合は全て処理）'
    )

    args = parser.parse_args()

    # dry-runがTrueの場合はdry_run=True
    dry_run = not args.execute

    cleaner = DuplicateItemsCleaner(dry_run=dry_run, gender_filter=args.gender)

    try:
        cleaner.run()
    except KeyboardInterrupt:
        print("\n\n❌ 処理が中断されました。")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
