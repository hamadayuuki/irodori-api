# Prompts Directory

このディレクトリには、Gemini APIで使用するプロンプトテキストファイルが格納されています。

## 📁 ファイル一覧

### チャット・相談系
- **chat_coordinate_advice.txt** - テキストのみのファッション相談
- **chat_coordinate_advice_with_image.txt** - 画像付きファッション相談

### コーディネート推薦系
- **generate_recommend_reasons.txt** - 推薦理由生成（150文字以内）

### ファッションレビュー系（並列処理）
- **generate_review_parallel.txt** - キャッチフレーズ＆レビュー生成
- **generate_tags_parallel.txt** - タグ生成（7つ）
- **extract_items_parallel.txt** - アイテム抽出

### アイテム抽出系
- **extract_coordinate_items.txt** - コーディネート画像からアイテム抽出

### 分析系
- **analyze_recent_coordinates.txt** - 最近のコーディネート傾向分析（100文字）

### ユーザーインサイト系
- **user_insight_intro.txt** - インサイト生成プロンプトのイントロ部分
- **user_insight_output_instructions.txt** - インサイト生成の出力指示（200-300文字）

## 🔧 使用方法

### 基本的な読み込み

```python
from prompt_loader import get_prompt_loader

# プロンプトローダーを取得
loader = get_prompt_loader()

# プロンプトを読み込み
prompt = loader.load("chat_coordinate_advice")
```

### 変数を含むプロンプトのフォーマット

プロンプトファイル内で `{variable_name}` 形式の変数を使用できます。

**例: chat_coordinate_advice.txt**
```
質問: {question}
性別: {gender_str}
```

**Pythonコード:**
```python
prompt = loader.format(
    "chat_coordinate_advice",
    question="どんなコーデがおすすめですか？",
    gender_str="メンズ"
)
```

### キャッシュのクリア

プロンプトファイルを更新した場合、キャッシュをクリアしてください：

```python
loader = get_prompt_loader()
loader.clear_cache()
```

## 📝 プロンプト編集ガイドライン

### 1. ファイル命名規則
- **snake_case** を使用
- 機能を明確に表す名前
- `.txt` 拡張子

### 2. 変数の使用
- 動的な値は `{variable_name}` 形式で記述
- 変数名は明確でわかりやすく

### 3. フォーマット
- UTF-8 エンコーディング
- 適切な改行とインデント
- 出力形式はJSON形式で記述

### 4. コメント
- プロンプト内にコメントを含める場合は `# コメント` 形式

## 🔄 API対応表

| エンドポイント | 使用プロンプトファイル |
|---------------|---------------------|
| `POST /chat` | `chat_coordinate_advice.txt`<br>`chat_coordinate_advice_with_image.txt` |
| `POST /recommend-coordinates` | `generate_recommend_reasons.txt` |
| `POST /api/fashion_review` | `generate_review_parallel.txt`<br>`generate_tags_parallel.txt`<br>`extract_items_parallel.txt` |
| `POST /api/analyze-recent-coordinate` | `analyze_recent_coordinates.txt` |
| `GET /api/user-insight` | `user_insight_intro.txt`<br>`user_insight_output_instructions.txt` |

## 🛠️ トラブルシューティング

### プロンプトファイルが見つからない

**エラー**: `FileNotFoundError: Prompt file not found`

**解決策**:
1. ファイルが `prompts/` ディレクトリに存在するか確認
2. ファイル名が正しいか確認（拡張子 `.txt` を除く）
3. ファイルのパーミッションを確認

### 変数が置き換えられない

**原因**: `format()` ではなく `load()` を使用している

**解決策**:
```python
# ❌ 間違い
prompt = loader.load("chat_coordinate_advice")

# ✅ 正しい
prompt = loader.format(
    "chat_coordinate_advice",
    question="質問内容",
    gender_str="メンズ"
)
```

## 📚 参考

- プロンプトローダーの実装: `prompt_loader.py`
- Gemini APIラッパー: `gemini_service.py`
- ユーザーインサイト: `user_insight_service.py`
