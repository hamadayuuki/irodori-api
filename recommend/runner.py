import joblib
import json
from RecommendTfidfVectorizer import recommend  # リネームしたファイルから関数をインポート

# 1. モデルのロード (--model)
# 毎回ロードすると重いため、Webアプリ等では起動時に1回だけ行うのが一般的です
model_path = "./men/men_model.joblib"
model = joblib.load(model_path)

# 2. 推論の実行
# コマンドライン引数を関数の引数として渡します
result = recommend(
    model=model,
    input_type="ボトムス",           # --input_type
    category="ワイドパンツ",         # --category
    text="ブラックのワイドパンツ",    # --text
    num_outfits=5,                  # --outfits_num
    num_candidates=10               # --candidates_num
)

# 3. 結果の表示 (JSON形式)
print(json.dumps(result, ensure_ascii=False, indent=2))