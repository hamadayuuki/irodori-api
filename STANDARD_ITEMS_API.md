# Standard Items API 仕様

## 概要

standard-items（標準アイテム）をFirebase Storage & Firestoreにアップロードし、APIで取得できるようにする機能です。

## データ構造

### ディレクトリ構成

```
/Users/yuki.hamada/Desktop/IRODORI/data/item/standard-items/
├── men/
│   ├── アウター_Gジャン_インディゴ.png
│   ├── アウター_MA-1_オリーブグリーン.png
│   ├── トップス_Tシャツ_グレー.png
│   └── ... (計41アイテム)
└── women/
    ├── アウター_Gジャン_インディゴ.png
    ├── アウター_カーディガン_オレンジ.png
    ├── トップス_Tシャツ_グレー.png
    └── ... (計45アイテム)
```

**ファイル命名規則**: `{カテゴリ}_{サブカテゴリ}_{色}.png`

例:
- `アウター_Gジャン_インディゴ.png` → main_category: "アウター", sub_category: "Gジャン", color: "インディゴ"
- `トップス_Tシャツ_グレー.png` → main_category: "トップス", sub_category: "Tシャツ", color: "グレー"

---

## Firestore コレクション

### `items` コレクション（既存コレクションに追加）

標準アイテムは既存の `items` コレクションに以下のフィールドで格納されます：

**ドキュメントID**: 自動生成UUID

**フィールド構造**:
```json
{
  "filename": "アウター_Gジャン_インディゴ.png",
  "storage_path": "standard-items/men/アウター_Gジャン_インディゴ.png",
  "storage_url": "https://storage.googleapis.com/...",
  "main_category": "アウター",
  "sub_category": "Gジャン",
  "color": "インディゴ",
  "gender": "men",
  "is_standard": true,
  "file_size": 381225,
  "file_hash": "abc123...",
  "uploaded_at": TIMESTAMP,
  "metadata": {},
  "tags": [],
  "is_active": true
}
```

**新規フィールド** ✨:
- `gender`: "men" または "women"（性別）
- `is_standard`: `true`（標準アイテムフラグ）

**既存フィールド**:
- `filename`: ファイル名
- `storage_path`: Firebase Storage内のパス
- `storage_url`: 公開URL
- `main_category`: メインカテゴリ（アウター、トップス、ボトムス等）
- `sub_category`: サブカテゴリ（Gジャン、Tシャツ等）
- `color`: 色（ブラック、ホワイト、インディゴ等）
- `file_size`: ファイルサイズ（バイト）
- `file_hash`: MD5ハッシュ値（重複チェック用）
- `uploaded_at`: アップロード日時
- `metadata`: メタデータ（空オブジェクト）
- `tags`: タグ配列（空配列）
- `is_active`: アクティブフラグ（true）

---

## Firebase Storage パス

**パス構造**: `standard-items/{gender}/{filename}`

例:
- `standard-items/men/アウター_Gジャン_インディゴ.png`
- `standard-items/women/トップス_Tシャツ_グレー.png`

---

## アップロードスクリプト

### `upload_standard_items.py`

**場所**: `/Users/yuki.hamada/Desktop/backend/irodori-api/upload_standard_items.py`

**実行方法**:
```bash
cd /Users/yuki.hamada/Desktop/backend/irodori-api
python3 upload_standard_items.py
```

**動作**:
1. `standard-items/men/` および `standard-items/women/` から全画像を取得
2. ファイル名をパースして `main_category`, `sub_category`, `color` を抽出
3. Firebase Storageにアップロード（パス: `standard-items/{gender}/{filename}`）
4. Firestoreの `items` コレクションにドキュメントを作成
5. 統計情報を `statistics/standard_items_summary` に保存
6. 結果を `upload_standard_items_results_{timestamp}.json` に保存

**出力例**:
```
[2026-03-14 19:30:00] INFO - Men's アイテム検索: /Users/yuki.hamada/Desktop/IRODORI/data/item/standard-items/men
[2026-03-14 19:30:00] INFO - Women's アイテム検索: /Users/yuki.hamada/Desktop/IRODORI/data/item/standard-items/women
[2026-03-14 19:30:00] INFO - 見つかったアイテム数: 84
[2026-03-14 19:30:00] INFO -   Men's: 40
[2026-03-14 19:30:00] INFO -   Women's: 44
アップロード中: 100%|████████████████████| 84/84 [00:45<00:00,  1.85it/s]
[2026-03-14 19:30:45] INFO - アップロード完了:
[2026-03-14 19:30:45] INFO - 成功: 84
[2026-03-14 19:30:45] INFO - 失敗: 0
```

---

## API エンドポイント

### 1. 標準アイテム取得

**エンドポイント**: `GET /api/standard-items`

**クエリパラメータ**:
- `gender` (optional): "men" または "women"
- `main_category` (optional): メインカテゴリ（例: "アウター"）
- `sub_category` (optional): サブカテゴリ（例: "Gジャン"）
- `color` (optional): 色（例: "ブラック"）
- `limit` (optional): 取得件数上限（デフォルト: 100）

**レスポンス例**:
```json
{
  "status": "success",
  "total_count": 5,
  "items": [
    {
      "id": "abc123",
      "filename": "アウター_Gジャン_インディゴ.png",
      "storage_url": "https://storage.googleapis.com/irodori-e5c71.firebasestorage.app/standard-items/men/アウター_Gジャン_インディゴ.png",
      "main_category": "アウター",
      "sub_category": "Gジャン",
      "color": "インディゴ",
      "gender": "men",
      "is_standard": true,
      "file_size": 381225,
      "uploaded_at": "2026-03-14T19:30:00Z"
    },
    ...
  ],
  "filters": {
    "gender": "men",
    "main_category": "アウター",
    "sub_category": null,
    "color": null,
    "limit": 100
  }
}
```

**使用例**:
```bash
# 全アイテムを取得
curl "http://localhost:8000/api/standard-items"

# Men's アイテムのみ
curl "http://localhost:8000/api/standard-items?gender=men"

# Women's のアウターのみ
curl "http://localhost:8000/api/standard-items?gender=women&main_category=アウター"

# Men's の黒いTシャツ
curl "http://localhost:8000/api/standard-items?gender=men&main_category=トップス&sub_category=Tシャツ&color=ブラック"
```

---

### 2. カテゴリ一覧取得

**エンドポイント**: `GET /api/standard-items/categories`

**クエリパラメータ**:
- `gender` (optional): "men" または "women"

**レスポンス例**:
```json
{
  "status": "success",
  "gender": "men",
  "total_count": 40,
  "categories": {
    "アウター": {
      "count": 11,
      "sub_categories": {
        "Gジャン": 1,
        "MA-1": 1,
        "ステンカラーコート": 1,
        "ダウンジャケット": 1,
        "テーラードジャケット": 1,
        "トレンチコート": 1,
        "マウンテンパーカー": 1,
        "ライダースジャケット": 1,
        "レザージャケット": 1
      },
      "colors": ["インディゴ", "オリーブグリーン", "ネイビー", "ブラック", "ベージュ"]
    },
    "トップス": {
      "count": 15,
      "sub_categories": {
        "Tシャツ": 3,
        "Vネックセーター": 1,
        "カーディガン": 1,
        "クルーネックニット": 1,
        "シャツ": 1,
        ...
      },
      "colors": ["グレー", "ネイビー", "ブラック", "ホワイト", "ベージュ"]
    },
    ...
  }
}
```

**使用例**:
```bash
# 全カテゴリを取得
curl "http://localhost:8000/api/standard-items/categories"

# Men's カテゴリのみ
curl "http://localhost:8000/api/standard-items/categories?gender=men"

# Women's カテゴリのみ
curl "http://localhost:8000/api/standard-items/categories?gender=women"
```

---

### 3. ヘルスチェック

**エンドポイント**: `GET /health/standard-items`

**レスポンス例**:
```json
{
  "status": "healthy",
  "message": "Standard items service is running",
  "sample_item_exists": true
}
```

---

## 実装ファイル

### 1. `upload_standard_items.py`
- **役割**: アップロードスクリプト
- **クラス**: `StandardItemsUploader`
- **メソッド**:
  - `parse_filename()`: ファイル名からカテゴリ情報を抽出
  - `get_standard_items()`: men/ と women/ から全アイテムを取得
  - `upload_item()`: 単一アイテムをStorage & Firestoreにアップロード
  - `upload_all()`: 全アイテムをアップロード
  - `create_category_summary()`: 統計情報を作成

### 2. `standard_items_service.py`
- **役割**: ビジネスロジック（Firestoreからアイテム取得）
- **クラス**: `StandardItemsService`
- **メソッド**:
  - `get_standard_items()`: フィルタ付きアイテム取得
  - `get_categories()`: カテゴリ一覧取得

### 3. `models.py`
- **追加モデル**:
  - `StandardItem`: アイテム情報
  - `StandardItemsResponse`: API レスポンス

### 4. `main.py`
- **追加エンドポイント**:
  - `GET /api/standard-items`
  - `GET /api/standard-items/categories`
  - `GET /health/standard-items`

---

## Firestore クエリ制限

**重要**: 複数フィールドでのフィルタリングにはFirestoreインデックスが必要になる可能性があります。

### 必要になる可能性のあるインデックス

以下のクエリパターンを使用する場合、インデックスが必要です：

1. `is_standard=true` + `gender=men` + `main_category=アウター`
2. `is_standard=true` + `gender=women` + `main_category=トップス` + `sub_category=Tシャツ`

**現状**: Pythonでソートしているため、基本的なクエリはインデックス不要で動作します。

**将来的な最適化**: 頻繁に使用されるクエリパターンが明らかになったら、Firestore Consoleでインデックスを作成することを推奨します。

---

## テスト方法

### 1. アップロードスクリプトの実行

```bash
cd /Users/yuki.hamada/Desktop/backend/irodori-api
python3 upload_standard_items.py
```

**確認項目**:
- [ ] 84件のアイテムがアップロードされる（men: 40, women: 44）
- [ ] Firebase Storageに `standard-items/men/` と `standard-items/women/` が作成される
- [ ] Firestoreの `items` コレクションに `is_standard=true` のドキュメントが追加される
- [ ] `upload_standard_items_results_{timestamp}.json` が生成される

### 2. API テスト

```bash
# ヘルスチェック
curl "http://localhost:8000/health/standard-items"

# 全アイテム取得
curl "http://localhost:8000/api/standard-items?limit=10"

# Men's アイテム取得
curl "http://localhost:8000/api/standard-items?gender=men&limit=10"

# カテゴリ一覧取得
curl "http://localhost:8000/api/standard-items/categories?gender=men"
```

---

## まとめ

### 実装完了内容

✅ **アップロードスクリプト**: `upload_standard_items.py`
- men/ と women/ からアイテムを自動取得
- ファイル名からカテゴリ情報を自動抽出
- Firebase Storage & Firestoreに自動アップロード

✅ **サービス層**: `standard_items_service.py`
- フィルタ付きアイテム取得
- カテゴリ一覧取得

✅ **API エンドポイント**:
- `GET /api/standard-items` - アイテム取得（フィルタ対応）
- `GET /api/standard-items/categories` - カテゴリ一覧
- `GET /health/standard-items` - ヘルスチェック

✅ **Firestore設計**:
- 既存の `items` コレクションに統合
- `gender` と `is_standard` フィールドを追加
- 統計情報を `statistics/standard_items_summary` に保存

### データ件数

- **Men's**: 40アイテム
- **Women's**: 44アイテム
- **合計**: 84アイテム

### Storage パス

- `standard-items/men/{filename}`
- `standard-items/women/{filename}`
