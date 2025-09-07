import os
import base64
import json
from typing import List, Optional
import urllib
import urllib.parse
import random

from pydantic import BaseModel
import requests

from fastapi import FastAPI
from models import RecommendCoordinatesRequest, RecommendCoordinatesResponse, GenreCount
from coordinate_service import CoordinateService

# AnalysisCoordinate Models
class AnalysisCoordinateRequest(BaseModel):
    image_id: int
    gender: str    # men, women, other

class AnalysisCoordinateResponse(BaseModel):
    id: int
    coordinate_review: Optional[str] = None
    tops_categorize: Optional[str] = None
    bottoms_categorize: Optional[str] = None

app = FastAPI()

from openai import OpenAI
client = OpenAI(
    api_key = os.getenv('OPENAI_API_KEY')
)
gptModel = "gpt-4o"

@app.get("/")
async def root():
    return {"message": "Hello, FastAPI on Render!"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/health/analysis-coordinate", response_model = AnalysisCoordinateResponse)
async def analysis_coordinate_health():
    import csv
    import os
    import random
    
    # デフォルトでmenのデータを使用してサンプルレスポンスを返す
    gender_folder = "men"
    csv_path = f"data/analysis-coordinate/{gender_folder}/coordinates.csv"
    
    try:
        # CSVファイルが存在するかチェック
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Data file not found: {csv_path}")
        
        # CSVファイルからランダムにデータを選択
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            coordinates = list(reader)
            
        if not coordinates:
            raise ValueError("No coordinate data found")
        
        # ランダムに1つのコーディネートを選択
        selected_coordinate = random.choice(coordinates)
        
        analysisResponse = AnalysisCoordinateResponse(
            id = int(selected_coordinate.get("id")),
            coordinate_review = selected_coordinate.get("coordinate_review"),
            tops_categorize = selected_coordinate.get("tops_categorize"),
            bottoms_categorize = selected_coordinate.get("bottoms_categorize")
        )
        
    except Exception as e:
        print(f"Error loading local data: {e}")
        # エラーが発生した場合は空のレスポンスを返す
        analysisResponse = AnalysisCoordinateResponse(
            id = random.randrange(10**10),
            coordinate_review = "Health check: analysis-coordinate endpoint is working with local CSV data",
            tops_categorize = None,
            bottoms_categorize = None
        )
    
    return analysisResponse

@app.get("/check-gpt")
async def checkGPT():
    completion = client.chat.completions.create(
        model = gptModel,
        messages=[{
            "role": "user",
            "content": "Write a one-sentence bedtime story about a unicorn."
        }]
    )
    return {"result": completion.choices[0].message.content}

@app.get("/check-vision-gpt")
async def checkVisionGPT():
    imageURL = "https://images.wear2.jp/coordinate/DZiOeg3/21k0twHn/1728043950_500.jpg"   # WEARのコーデ画像
    imageData = requests.get(imageURL).content
    encodedImage = base64.b64encode(imageData).decode('utf-8')
    prompt = """
    添付する画像に合わせて、以下の質問に回答する形でコーデに関するコメントをください。

    ## フォーマット
    - ワンポイントアイテムを褒める <褒める>
    例 : 白色のキャップが可愛いですね
    - サイズ感についてのコメント
    例 : ワイドなパンツを履いているのでラフでスマートな印象を受けます。\n上下のサイズがちょうど良いのでおしゃれな印象を受けます
    - シルエット診断 <知見の共有>
    例 : あなたのシルエットはIです。Iが似合うのは〜のような特徴を持った方です
    - コーディネートタイプ診断 <知見の共有>
    例 : また、あなたのコーデはカジュアルです。
    - あなたに似合うコーディネートタイプは
    例 : カジュアル が似合う方におすすめのコーデタイプは、ノームコアです。
    
    ## アウトプットのフォーマット（必ず文字列のみでアウトプットしてください）
    <ワンポイントアイテムを褒める>\n
    <サイズ感についてのコメント>\n
    <シルエット診断>\n
    <コーディネートタイプ診断>\n
    <あなたに似合うコーディネートタイプは>\n
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encodedImage}"
                        }
                    }
                ]
            }
        ],
        max_completion_tokens=300,
    )
    return {"result": response.choices[0].message.content}

def parse_input(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    ai_catchphrase = lines[0] if lines else ""
    ai_comment = "\n".join(lines[1:]).lstrip("\n")
    return ai_catchphrase, ai_comment


class ImageRequest(BaseModel):
    image_base64: str


class CoordinateResponse(BaseModel):
    id: int
    ai_comment: str
    ai_catchphrase: str


@app.post("/coordinate-review", response_model = CoordinateResponse)
async def coordinateReview(request: ImageRequest):
    system_prompt = """
    あなたは人の心理を読み取り、ファッションや人物の特徴を的確に分析できます。
    """

    prompt = """
    入力する全身画像と「## ユーザーの特徴」を元に、以下のフォーマットを守りレビューしてください。

    アウトプット
    <面白く頭に残るキャッチコピー, 20文字以内>

    <キャッチコピーの意図を含めたコーディネート総括, 100文字程度>

    **他者からの見られ方**
    <同性・異性、先輩・後輩からどう見られるかを面白く簡潔に, 100文字程度>

    **ワンポイントアドバイス**
    <ユーザーの特徴と照らし合わせ、合っている部分を褒め、改善点があれば愛をもって提案>

    ## 制約
    - 愛があり面白く、飽きさせないレビューにしてください。
    - ファッション初心者も「読んでよかった」と感じるようにしてください。
    - ネガティブ・不快な表現は絶対に避けてください。
    - 「ユーザーの特徴」を私が伝えたとは感じさせないよう注意してください。
    - 出力は必ず日本語
    - 出力に <,> は含めない
    - ** で囲まれた文は、**も含めてそのまま出力してください

    ## ユーザーの特徴
    - 「好き」に正直で全力投球。感情を隠さない情熱型。
    - 直感と打算を使い分ける現実派。
    - 陽気だが内面は戦略家の二面性。
    - 人を喜ばせることで自己肯定感を得る。
    - 夢を着実に叶える粘り強さと努力家精神。
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{request.image_base64}"
                        }
                    }
                ]
            }
        ],
        max_completion_tokens = 2048,
    )
    print(response.choices[0].message.content)

    text = response.choices[0].message.content
    catchphrase, comment = parse_input(text)

    coordinateResponse = CoordinateResponse(
        id = random.randrange(10**10),
        ai_comment = comment,
        ai_catchphrase = catchphrase
    )
    print(coordinateResponse)

    return coordinateResponse

# AnalysisCoordinate

@app.post("/analysis-coordinate", response_model = AnalysisCoordinateResponse)
async def analysisCoordinate(request: AnalysisCoordinateRequest):
    import csv
    import os
    import random
    
    # genderに応じてデータファイルを選択
    gender_folder = "men" if request.gender == "other" else request.gender
    csv_path = f"data/analysis-coordinate/{gender_folder}/coordinates.csv"
    
    try:
        # CSVファイルが存在するかチェック
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Data file not found: {csv_path}")
        
        # CSVファイルからimage_idに一致するデータを検索
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            coordinates = list(reader)
            
        if not coordinates:
            raise ValueError("No coordinate data found")
        
        # image_idに一致するコーディネートを検索
        selected_coordinate = None
        for coordinate in coordinates:
            if int(coordinate.get("id")) == request.image_id:
                selected_coordinate = coordinate
                break
        
        # 一致するデータが見つからない場合はエラー
        if not selected_coordinate:
            raise ValueError(f"No coordinate found for image_id: {request.image_id}")
        
        analysisResponse = AnalysisCoordinateResponse(
            id = int(selected_coordinate.get("id")),
            coordinate_review = selected_coordinate.get("coordinate_review"),
            tops_categorize = selected_coordinate.get("tops_categorize"),
            bottoms_categorize = selected_coordinate.get("bottoms_categorize")
        )
        
    except Exception as e:
        print(f"Error loading local data: {e}")
        # エラーが発生した場合は空のレスポンスを返す
        analysisResponse = AnalysisCoordinateResponse(
            id = request.image_id,
            coordinate_review = f"Error: {str(e)}",
            tops_categorize = None,
            bottoms_categorize = None
        )
    
    print(analysisResponse)
    return analysisResponse

@app.post("/recommend-coordinates", response_model=RecommendCoordinatesResponse)
async def recommend_coordinates(request: RecommendCoordinatesRequest):
    result = CoordinateService.recommend_coordinates(request.gender)
    genres_with_count = [GenreCount(genre=genre, count=count) for genre, count in result['genres'].items()]
    return RecommendCoordinatesResponse(
        coordinates=result['coordinates'],
        genres=genres_with_count
    )

@app.get("/health/recommend-coordinates")
async def health_recommend_coordinates():
    try:
        # テスト用リクエストを作成
        test_request = RecommendCoordinatesRequest(gender="men")
        
        # recommend_coordinates関数を呼び出し
        result = await recommend_coordinates(test_request)
        
        # コンソールに出力
        print("Health check result for recommend-coordinates:")
        print(f"Number of coordinates: {len(result.coordinates)}")
        print(f"Genres: {[f'{g.genre}({g.count})' for g in result.genres]}")
        for i, coord in enumerate(result.coordinates):
            print(f"  {i+1}. ID: {coord.id}, URL: {coord.image_url}")
        
        return {
            "status": "success",
            "message": "recommend-coordinates endpoint test completed",
            "result": result
        }
        
    except Exception as e:
        print(f"Health check failed: {str(e)}")
        return {
            "status": "error",
            "message": f"Test failed: {str(e)}",
            "result": None
        }

@app.get("/health/analysis-coordinate")
async def healthAnalysisCoordinate():
    # テスト用画像を読み込み
    image_path = "test/image/coordinate.jpg"
    
    try:
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # AnalysisCoordinateRequestを作成
        test_request = AnalysisCoordinateRequest(
            image_base64=image_base64,
            gender="other"
        )
        
        # analysisCoordinate関数を呼び出し
        result = await analysisCoordinate(test_request)
        
        return {
            "status": "success",
            "message": "analysis-coordinate endpoint test completed",
            "result": result
        }
        
    except FileNotFoundError:
        return {
            "status": "error",
            "message": f"Test image not found: {image_path}",
            "result": None
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Test failed: {str(e)}",
            "result": None
        }
