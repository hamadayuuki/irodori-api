# User Insight API 仕様書

## 概要

ユーザーのファッションタイプ診断結果、動物占い結果、実際のコーディネート履歴を統合して、Gemini 2.5-flash-lite でパーソナライズされたインサイトを生成します。

---

## 1. インサイト生成 API

### エンドポイント
```
GET /api/user-insight
```

### リクエスト

#### クエリパラメータ

| パラメータ | 型 | 必須 | 説明 |
|-----------|----|----|------|
| `userid` | string | ✅ | ユーザーID |

#### リクエスト例

```bash
GET /api/user-insight?userid=user-123
```

```bash
curl -X GET "http://localhost:8000/api/user-insight?userid=user-123" \
  -H "accept: application/json"
```

---

### レスポンス

#### レスポンスモデル: `UserInsightResponse`

```json
{
  "status": "success",
  "user_id": "user-123",
  "insight_id": "550e8400-e29b-41d4-a716-446655440000",
  "fashion_type": {
    "type_code": "TPAE",
    "type_name": "トレンド・エディター",
    "description": "最先端のトレンドをいち早く取り入れ、自分らしく編集するスタイリスト。流行に敏感でありながら、自分の美学を大切にし、トレンドアイテムを自分らしく着こなすことができるタイプです。",
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
    "base_personality": "エネルギッシュで行動力があり、リーダーシップを発揮するタイプ。自信に満ち溢れ、目標に向かって突き進む強い意志を持っています。周囲を引っ張る力があり、困難な状況でも前向きに取り組むことができます。",
    "life_tendency": "人生において、常に挑戦を求め、新しいことに果敢にチャレンジします。リーダーとしての資質があり、周囲から頼りにされることが多いでしょう。ただし、時には独断的になりやすいので、周囲の意見にも耳を傾けることが大切です。",
    "female_feature": "キャリア志向が強く、仕事で成功を収めることに情熱を注ぎます。自立心が強く、自分の道を切り開いていく力があります。",
    "male_feature": "頼りがいのあるリーダータイプ。仕事でも私生活でも周囲を引っ張っていく存在です。",
    "love_tendency": "恋愛においても積極的で、情熱的なアプローチをします。パートナーには自分と同じくらい強い意志を持つ人を求めます。"
  },
  "insight": "あなたは**最先端のトレンドを自分らしく取り入れる個性派**タイプですね！実際のコーディネートを見ると、モノトーンを基調としながらもチェック柄やダメージ加工でアクセントを加える、計算されたスタイルが印象的です。\n\n**あなたの強み:**\n- シンプルながらも個性を忘れない洗練されたセンス\n- トレンドアイテムを自分らしく着こなす応用力\n- モノトーンコーデに遊び心をプラスするバランス感覚\n\n直近のコーデから、都会的でクールな印象を保ちつつ、さりげない遊び心を忘れないあなたのファッション哲学が伝わります！今後は、カラーアイテムを1点投入することで、より幅広いスタイル表現ができそうです。",
  "generated_at": "2026-03-12T19:30:00.123456"
}
```

#### フィールド説明

| フィールド | 型 | 説明 |
|-----------|----|----|
| `status` | string | ステータス（`"success"` または `"no_data"`） |
| `user_id` | string | ユーザーID |
| `insight_id` | string \| null | インサイトID（FirestoreドキュメントID） |
| `fashion_type` | object \| null | ファッションタイプ情報 |
| `fashion_type.type_code` | string | タイプコード（4文字、例: `"TPAE"`） |
| `fashion_type.type_name` | string | タイプ名（例: `"トレンド・エディター"`） |
| `fashion_type.description` | string | タイプの詳細説明 |
| `fashion_type.core_stance` | string | 核心スタンス（例: `"流行・自己起点・美学・節約"`） |
| `fashion_type.group` | string | グループ名（例: `"流行・自己起点"`） |
| `fashion_type.group_color` | string | グループカラー（例: `"ピンク"`） |
| `fashion_type.scores` | object | 5軸のスコア |
| `fashion_type.scores.trend_score` | float | トレンド感度スコア（1.0-5.0） |
| `fashion_type.scores.self_score` | float | 自己表現スコア（1.0-5.0） |
| `fashion_type.scores.social_score` | float | 社会調和スコア（1.0-5.0） |
| `fashion_type.scores.function_score` | float | 機能重視スコア（1.0-5.0） |
| `fashion_type.scores.economy_score` | float | 投資志向スコア（1.0-5.0） |
| `animal_fortune` | object \| null | 動物占い情報 |
| `animal_fortune.animal_number` | integer | 動物番号（1-60） |
| `animal_fortune.animal` | string | 動物種類（例: `"虎（ブラウン）"`） |
| `animal_fortune.animal_name` | string | 動物キャラクター名（例: `"パワフルな虎"`） |
| `animal_fortune.base_personality` | string \| null | 基本性格 |
| `animal_fortune.life_tendency` | string \| null | 人生傾向 |
| `animal_fortune.female_feature` | string \| null | 女性特徴 |
| `animal_fortune.male_feature` | string \| null | 男性特徴 |
| `animal_fortune.love_tendency` | string \| null | 恋愛傾向 |
| `insight` | string | Gemini生成のインサイト（200-300文字、改行`\n`、太字`**text**`を含む） |
| `generated_at` | string | 生成日時（ISO 8601形式） |

---

#### ステータス別レスポンス

##### 1. **成功時** (`status: "success"`)

```json
{
  "status": "success",
  "user_id": "user-123",
  "insight_id": "550e8400-e29b-41d4-a716-446655440000",
  "fashion_type": { /* ... */ },
  "animal_fortune": { /* ... */ },
  "insight": "あなたは**最先端のトレンドを...",
  "generated_at": "2026-03-12T19:30:00.123456"
}
```

##### 2. **データ不足時** (`status: "no_data"`)

ファッションタイプ診断または動物占いが未実施の場合。

```json
{
  "status": "no_data",
  "user_id": "user-123",
  "insight_id": null,
  "fashion_type": null,
  "animal_fortune": null,
  "insight": "ファッションタイプ診断または動物占いを実施してください。",
  "generated_at": "2026-03-12T19:30:00.123456"
}
```

---

### エラーレスポンス

#### 500 Internal Server Error

```json
{
  "detail": "Internal server error: [エラー詳細]"
}
```

---

## 2. インサイト履歴取得 API

### エンドポイント
```
GET /api/user-insight/history
```

### リクエスト

#### クエリパラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|----|----|----------|------|
| `userid` | string | ✅ | - | ユーザーID |
| `limit` | integer | ❌ | 10 | 取得件数（最大値なし） |

#### リクエスト例

```bash
GET /api/user-insight/history?userid=user-123&limit=5
```

```bash
curl -X GET "http://localhost:8000/api/user-insight/history?userid=user-123&limit=5" \
  -H "accept: application/json"
```

---

### レスポンス

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
      "insight": "あなたは**最先端のトレンドを自分らしく取り入れる個性派**タイプですね！実際のコーディネートを見ると...",
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

#### フィールド説明

| フィールド | 型 | 説明 |
|-----------|----|----|
| `status` | string | ステータス（`"success"`） |
| `user_id` | string | ユーザーID |
| `count` | integer | 取得件数 |
| `history` | array | インサイト履歴（新しい順） |
| `history[].insight_id` | string | インサイトID |
| `history[].user_id` | string | ユーザーID |
| `history[].fashion_type_code` | string \| null | ファッションタイプコード |
| `history[].animal_number` | integer \| null | 動物番号 |
| `history[].insight` | string | インサイトテキスト |
| `history[].generated_at` | string | 生成日時（ISO 8601形式） |

---

## 3. Health Check API

### エンドポイント
```
GET /health/user-insight
```

### リクエスト

パラメータなし

```bash
GET /health/user-insight
```

```bash
curl -X GET "http://localhost:8000/health/user-insight" \
  -H "accept: application/json"
```

---

### レスポンス

```json
{
  "status": "success",
  "message": "user-insight endpoint test completed",
  "test_params": {
    "user_id": "test-user-health-insight"
  },
  "result": {
    "status": "success",
    "user_id": "test-user-health-insight",
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
    "insight": "あなたは**最先端のトレンドを...",
    "generated_at": "2026-03-12T19:30:00.123456",
    "gemini_available": true
  }
}
```

#### フィールド説明

| フィールド | 型 | 説明 |
|-----------|----|----|
| `status` | string | ステータス（`"success"` または `"error"`） |
| `message` | string | テスト結果メッセージ |
| `test_params` | object | テストパラメータ |
| `test_params.user_id` | string | テストユーザーID |
| `result` | object | インサイト生成結果 |
| `result.gemini_available` | boolean | Gemini APIが利用可能か |

---

## 4. データフロー

### インサイト生成時のデータ取得順序

```
1. fashion-types コレクション
   ↓ user_id でフィルタ、created_at 降順ソート
   └→ 最新1件取得
       ↓
       └→ fashion-type-master から詳細取得（type_code で参照）

2. animal-fortunes コレクション
   ↓ user_id でフィルタ、created_at 降順ソート
   └→ 最新1件取得
       ↓
       └→ animal-master から詳細取得（animal_number で参照）

3. fashion-review コレクション ✨ NEW
   ↓ user_id でフィルタ、created_at 降順ソート
   └→ 最新7件取得
       ↓
       ├→ 直近3件: 詳細情報（最重要）
       └→ 4-7件目: 要約情報（参考）

4. Gemini 2.5-flash-lite でインサイト生成
   ↓
   └→ 上記3つのデータを統合したプロンプト

5. user-insights コレクションに保存
   ↓
   └→ insight_id を生成してレスポンス
```

---

## 5. 使用例

### TypeScript / JavaScript

```typescript
// 1. インサイト生成
const response = await fetch(
  `https://api.example.com/api/user-insight?userid=user-123`
);
const insight = await response.json();

console.log(insight.insight);
// "あなたは**最先端のトレンドを自分らしく取り入れる個性派**タイプですね！..."

// 2. インサイト履歴取得
const historyResponse = await fetch(
  `https://api.example.com/api/user-insight/history?userid=user-123&limit=5`
);
const history = await historyResponse.json();

console.log(`過去のインサイト: ${history.count}件`);
history.history.forEach((item, index) => {
  console.log(`${index + 1}. ${item.generated_at}: ${item.insight.substring(0, 50)}...`);
});
```

### Python

```python
import requests

# 1. インサイト生成
response = requests.get(
    "https://api.example.com/api/user-insight",
    params={"userid": "user-123"}
)
insight = response.json()

print(insight["insight"])

# 2. インサイト履歴取得
history_response = requests.get(
    "https://api.example.com/api/user-insight/history",
    params={"userid": "user-123", "limit": 5}
)
history = history_response.json()

print(f"過去のインサイト: {history['count']}件")
for item in history["history"]:
    print(f"{item['generated_at']}: {item['insight'][:50]}...")
```

### curl

```bash
# 1. インサイト生成
curl -X GET "https://api.example.com/api/user-insight?userid=user-123" \
  -H "accept: application/json"

# 2. インサイト履歴取得
curl -X GET "https://api.example.com/api/user-insight/history?userid=user-123&limit=5" \
  -H "accept: application/json"

# 3. Health Check
curl -X GET "https://api.example.com/health/user-insight" \
  -H "accept: application/json"
```

---

## 6. 注意事項

### 前提条件

1. **ファッションタイプ診断が完了していること**
   - `/api/fashion-type/diagnose` で診断実施
   - `fashion-types` コレクションにデータが存在

2. **動物占いが完了していること**
   - `/api/animal-fortune/diagnose` で占い実施
   - `animal-fortunes` コレクションにデータが存在

3. **Fashion Review（オプション）**
   - 0件でも動作するが、存在するとより具体的なインサイトが生成される
   - `/api/fashion-review` で投稿

### パフォーマンス

- **初回生成**: 約3-5秒（Gemini API呼び出し含む）
- **2回目以降**: 同じユーザーでも毎回新規生成（キャッシュなし）
- **Firestore読み取り**: 約10-15回（fashion-type, animal-fortune, fashion-review合計）
- **Firestore書き込み**: 1回（user-insights）

### 制限

- **Fashion Review取得**: 最大7件まで
- **Geminiプロンプトサイズ**: レビューコメント100文字まで切り詰め
- **インサイト文字数**: 200-300文字（Geminiに指示）

### セキュリティ

- 環境変数 `GOOGLE_GENAI_API_KEY` が必要
- Firestore認証が必要
- ユーザー認証は実装側で対応

---

## 7. まとめ

### エンドポイント一覧

| エンドポイント | メソッド | 用途 |
|---------------|---------|------|
| `/api/user-insight` | GET | インサイト生成 & Firestore保存 |
| `/api/user-insight/history` | GET | インサイト履歴取得 |
| `/health/user-insight` | GET | ヘルスチェック |

### データソース

1. ✅ ファッションタイプ診断結果
2. ✅ 動物占い結果
3. ✅ 実際のコーディネート履歴（最大7件、直近3件を重視）

### 出力

- 📝 Gemini 2.5-flash-lite 生成のパーソナライズされたインサイト
- 💾 Firestoreに自動保存（`user-insights` コレクション）
- 📊 履歴として蓄積され、後から参照可能
