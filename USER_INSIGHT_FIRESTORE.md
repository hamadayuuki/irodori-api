# User Insight Firestore 格納機能

## 概要

ユーザーインサイトをFirestoreに格納し、履歴として保存する機能を実装しました。

---

## Firestoreコレクション構造

### `user-insights` コレクション（新規追加）

ユーザーごとのインサイト履歴を保存します。

**ドキュメントID**: 自動生成UUID

**フィールド構造**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-123",
  "fashion_type_code": "TPAE",
  "animal_number": 45,
  "insight": "あなたは**最先端のトレンドを自分らしく取り入れる個性派**タイプですね！...",
  "generated_at": "2026-03-12T19:30:00.123456",
  "created_at": "2026-03-12T19:30:00.123456Z"  // Firestore SERVER_TIMESTAMP
}
```

**フィールド説明**:
- `id`: インサイトID（UUID）
- `user_id`: ユーザーID
- `fashion_type_code`: ファッションタイプコード（例: "TPAE"）- マスター参照用
- `animal_number`: 動物番号（1-60）- マスター参照用
- `insight`: Geminiで生成されたインサイトテキスト（200-300文字）
- `generated_at`: インサイト生成日時（ISO 8601形式の文字列）
- `created_at`: Firestore保存日時（サーバータイムスタンプ）

---

## API エンドポイント

### 1. インサイト生成 & Firestore保存

**エンドポイント**: `GET /api/user-insight?userid={user_id}`

**動作**:
1. ユーザーの最新ファッションタイプを取得
2. ユーザーの最新動物占い結果を取得
3. Gemini 2.5-flash-lite でインサイトを生成
4. **Firestoreの `user-insights` コレクションに保存** ✨ NEW
5. レスポンスを返す

**レスポンス例**:
```json
{
  "status": "success",
  "user_id": "user-123",
  "insight_id": "550e8400-e29b-41d4-a716-446655440000",  // ← NEW
  "fashion_type": {
    "type_code": "TPAE",
    "type_name": "トレンド・エディター",
    "description": "...",
    "core_stance": "流行・自己起点・美学・節約",
    "group": "流行・自己起点",
    "group_color": "ピンク",
    "scores": {
      "trend_score": 5.0,
      "self_score": 5.0,
      "social_score": 1.0,
      "function_score": 1.0,
      "economy_score": 5.0
    }
  },
  "animal_fortune": {
    "animal_number": 45,
    "animal": "虎（ブラウン）",
    "animal_name": "パワフルな虎",
    "base_personality": "...",
    "life_tendency": "..."
  },
  "insight": "あなたは**最先端のトレンドを自分らしく取り入れる個性派**タイプですね！動物占いの結果から、パワフルでリーダーシップのある性格が見えます。\n\n**おすすめスタイル:**\n- デザイナーズブランドの新作を誰よりも早く着こなす\n- 独創的なアイテムを主役にしたスタイル\n- トレンドを意識しつつ節約も重視するスマートな買い物\n\nパワフルで行動力のあるあなたには、ファッションで自分を表現することを大切にしつつ、賢く投資するスタイリングがぴったりです！",
  "generated_at": "2026-03-12T19:30:00.123456"
}
```

---

### 2. インサイト履歴取得

**エンドポイント**: `GET /api/user-insight/history?userid={user_id}&limit={limit}` ✨ NEW

**クエリパラメータ**:
- `userid` (required): ユーザーID
- `limit` (optional): 取得件数（デフォルト: 10）

**動作**:
1. Firestoreの `user-insights` コレクションからユーザーのインサイトを取得
2. 新しい順（`generated_at` 降順）でソート
3. 指定件数を返す

**レスポンス例**:
```json
{
  "status": "success",
  "user_id": "user-123",
  "count": 3,
  "history": [
    {
      "insight_id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "user-123",
      "fashion_type_code": "TPAE",
      "animal_number": 45,
      "insight": "あなたは**最先端のトレンドを自分らしく取り入れる個性派**タイプですね！...",
      "generated_at": "2026-03-12T19:30:00.123456"
    },
    {
      "insight_id": "660f9500-f30c-52e5-b827-557766551111",
      "user_id": "user-123",
      "fashion_type_code": "CRFE",
      "animal_number": 12,
      "insight": "あなたは**定番スタイルを機能的に着こなす実用派**タイプですね！...",
      "generated_at": "2026-03-10T15:20:00.123456"
    },
    {
      "insight_id": "770a0600-g40d-63f6-c938-668877662222",
      "user_id": "user-123",
      "fashion_type_code": "TPAQ",
      "animal_number": 23,
      "insight": "あなたは**最先端のトレンドを自分の美学で着こなすアーティスト**タイプですね！...",
      "generated_at": "2026-03-01T10:10:00.123456"
    }
  ]
}
```

---

## 実装ファイル

### 1. `user_insight_service.py`

**変更点**:
- `generate_insight()`: インサイト生成後にFirestoreに保存
- `get_insight_history()`: インサイト履歴を取得（新規メソッド）

**主要コード**:
```python
# インサイト生成 & Firestore保存
insight_id = str(uuid.uuid4())
insight_data = {
    "id": insight_id,
    "user_id": user_id,
    "fashion_type_code": fashion_type.get('type_code'),
    "animal_number": animal_fortune.get('animal_number'),
    "insight": insight_text,
    "generated_at": generated_at,
    "created_at": firestore.SERVER_TIMESTAMP
}
doc_ref = self.db.collection('user-insights').document(insight_id)
doc_ref.set(insight_data)
```

---

### 2. `models.py`

**変更点**:
- `UserInsightResponse`: `insight_id` フィールドを追加

```python
class UserInsightResponse(BaseModel):
    status: str
    user_id: str
    insight_id: Optional[str] = None  # ← NEW
    fashion_type: Optional[UserInsightFashionType] = None
    animal_fortune: Optional[UserInsightAnimalFortune] = None
    insight: str
    generated_at: str
```

---

### 3. `main.py`

**変更点**:
- `/api/user-insight/history` エンドポイントを追加（新規）

---

## データフロー

```
┌─────────────────────────────────────────────────────────┐
│ APIリクエスト: GET /api/user-insight?userid=user-123   │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ UserInsightService.generate_insight()                   │
│ 1. fashion-types から最新タイプ取得                      │
│ 2. animal-fortunes から最新占い取得                     │
│ 3. Gemini 2.5-flash-lite でインサイト生成               │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ Firestore 保存                                          │
│ Collection: user-insights                               │
│ Document ID: 550e8400-e29b-41d4-a716-446655440000       │
│ Fields:                                                 │
│   - id: インサイトID                                     │
│   - user_id: ユーザーID                                  │
│   - fashion_type_code: TPAE                             │
│   - animal_number: 45                                   │
│   - insight: "あなたは**最先端の..."                     │
│   - generated_at: "2026-03-12T19:30:00.123456"          │
│   - created_at: SERVER_TIMESTAMP                        │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ APIレスポンス                                            │
│ {                                                       │
│   "status": "success",                                  │
│   "insight_id": "550e8400-...",  // ← Firestore ID     │
│   "insight": "あなたは**最先端の...",                    │
│   ...                                                   │
│ }                                                       │
└─────────────────────────────────────────────────────────┘
```

---

## Firestoreコレクション全体図（更新版）

```
Firestore Database
├── 🎨 ファッションタイプ - マスターデータ（34件）
│   ├── fashion-type-master (16件)
│   ├── fashion-type-groups (4件)
│   ├── fashion-type-questions (10件)
│   └── fashion-type-axes (4件)
│
├── 🐾 動物占い - マスターデータ（165件）
│   ├── animal-master (60件)
│   └── animal-calendar (105件)
│
├── 👤 ユーザーデータ（可変）
│   ├── fashion-types (ユーザー診断結果)
│   ├── animal-fortunes (ユーザー占い結果)
│   └── user-insights (ユーザーインサイト履歴) ✨ NEW
│
└── 🔒 既存コレクション（保護対象 - 変更なし）
    ├── fashion-review (コーディネート履歴)
    ├── items (グローバルアイテム)
    ├── coordinates (レガシーデータ)
    └── users/{user_id}/items (ユーザークローゼット)
```

---

## 利用シーン

1. **初回インサイト生成**: ユーザーが診断後、初めてインサイトを見る
2. **インサイト再生成**: 診断結果が変わった場合、新しいインサイトを生成
3. **履歴参照**: 過去のインサイトを振り返る（例: 「3ヶ月前と比べてタイプが変わったか確認」）
4. **トレンド分析**: ユーザーのファッションタイプの変化を追跡

---

## 注意事項

- Firestoreへの保存に失敗してもAPIエラーにはならず、インサイトは返される
- インサイト履歴は `user_id` でのみフィルタリング（インデックス不要）
- `generated_at` でPython側でソートするため、Firestoreインデックスは不要
- Gemini APIキーは環境変数 `GOOGLE_GENAI_API_KEY` から取得

---

## テスト方法

### 1. インサイト生成テスト
```bash
curl -X GET "http://localhost:8000/api/user-insight?userid=test-user-001"
```

### 2. 履歴取得テスト
```bash
curl -X GET "http://localhost:8000/api/user-insight/history?userid=test-user-001&limit=5"
```

### 3. Healthチェック
```bash
curl -X GET "http://localhost:8000/health/user-insight"
```

---

## まとめ

✅ **実装完了内容**:
1. インサイト生成時に `user-insights` コレクションへ自動保存
2. レスポンスに `insight_id` を追加
3. インサイト履歴取得API (`/api/user-insight/history`) を新規追加
4. Firestoreインデックス不要な設計

✅ **新規コレクション**: `user-insights`

✅ **新規エンドポイント**: `GET /api/user-insight/history`
