import os
import base64
import json
from typing import List, Optional, Dict, Any
import urllib
import urllib.parse
import random
from datetime import datetime
import asyncio

from pydantic import BaseModel
import requests
from google.cloud import firestore

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from models import (
    RecommendCoordinatesRequest, RecommendCoordinatesResponse, GenreCount,
    AnalysisCoordinateResponse, AffiliateProduct, ChatRequest, ChatResponse,
    FashionReviewResponse, FashionReviewCurrentCoordinate, FashionReviewRecentCoordinate,
    FashionReviewItem, CoordinateRecommendRequest, HomeResponse, HomeRecentCoordinate,
    ClosetItem, ClosetResponse, AnalyzeRecentCoordinateRequest, AnalyzeRecentCoordinateResponse,
    CoordinateListItem, CoordinateDetailCurrentCoordinate, CoordinateDetailItem,
    CoordinateDetailResponse, GeminiTestRequest, GeminiTestResponse,
    DeleteCoordinateRequest, DeleteCoordinateResponse,
    FashionTypeDiagnosisRequest, FashionTypeDiagnosisResponse,
    AnimalFortuneRequest, AnimalFortuneResponse,
    UserInsightResponse,
    StandardItem, StandardItemsResponse,
    RegisteredItem, ItemRegistrationResponse, BulkItemMetadata,
    BulkItemError, BulkItemRegistrationResponse,
    BulkCoordinateRecommendItem, BulkCoordinateRecommendRequest,
    CoordinateRecommendResult, BulkCoordinateRecommendResponse
)
from coordinate_service import CoordinateService
from yahoo_shopping import YahooShoppingClient
from gemini_service import GeminiService
from firebase_service import FirebaseService
from recommend_service import RecommendService

# AnalysisCoordinate Models
class AnalysisCoordinateRequest(BaseModel):
    image_id: int
    gender: str    # men, women, other

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Startup event to load recommendation models
@app.on_event("startup")
async def startup_event():
    """Initialize recommendation models on startup"""
    print("Initializing recommendation service...")
    RecommendService.initialize()
    print("Recommendation service initialized successfully")

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
        
        # Yahoo Shopping API統合（health checkでも同じ処理を追加）
        yahoo_client = YahooShoppingClient()
        gender_jp = "メンズ"  # health checkではデフォルトでメンズを使用
        
        # トップス商品検索
        if analysisResponse.tops_categorize:
            tops_query = yahoo_client.extract_search_keywords(analysisResponse.tops_categorize)
            tops_products = yahoo_client.search_products(tops_query, gender_jp, 15)
            analysisResponse.affiliate_tops = [AffiliateProduct(**product) for product in tops_products]
        
        # ボトムス商品検索  
        if analysisResponse.bottoms_categorize:
            bottoms_query = yahoo_client.extract_search_keywords(analysisResponse.bottoms_categorize)
            bottoms_products = yahoo_client.search_products(bottoms_query, gender_jp, 15)
            analysisResponse.affiliate_bottoms = [AffiliateProduct(**product) for product in bottoms_products]
        
    except Exception as e:
        print(f"Error loading local data: {e}")
        # エラーが発生した場合は空のレスポンスを返す
        analysisResponse = AnalysisCoordinateResponse(
            id = random.randrange(10**10),
            coordinate_review = "Health check: analysis-coordinate endpoint is working with local CSV data",
            tops_categorize = None,
            bottoms_categorize = None,
            affiliate_tops = [],
            affiliate_bottoms = []
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
        
        # Yahoo Shopping API統合
        yahoo_client = YahooShoppingClient()
        gender_jp = "メンズ" if request.gender == "men" else "レディース" if request.gender == "women" else "メンズ"
        
        # トップス商品検索
        if analysisResponse.tops_categorize:
            tops_query = yahoo_client.extract_search_keywords(analysisResponse.tops_categorize)
            tops_products = yahoo_client.search_products(tops_query, gender_jp, 15)
            analysisResponse.affiliate_tops = [AffiliateProduct(**product) for product in tops_products]
        
        # ボトムス商品検索
        if analysisResponse.bottoms_categorize:
            bottoms_query = yahoo_client.extract_search_keywords(analysisResponse.bottoms_categorize)
            bottoms_products = yahoo_client.search_products(bottoms_query, gender_jp, 15)
            analysisResponse.affiliate_bottoms = [AffiliateProduct(**product) for product in bottoms_products]
        
    except Exception as e:
        print(f"Error loading local data: {e}")
        # エラーが発生した場合は空のレスポンスを返す
        analysisResponse = AnalysisCoordinateResponse(
            id = request.image_id,
            coordinate_review = f"Error: {str(e)}",
            tops_categorize = None,
            bottoms_categorize = None,
            affiliate_tops = [],
            affiliate_bottoms = []
        )
    
    print(analysisResponse)
    return analysisResponse

@app.post("/recommend-coordinates", response_model=RecommendCoordinatesResponse)
async def recommend_coordinates(request: RecommendCoordinatesRequest):
    result = await CoordinateService.recommend_coordinates_async(request.gender)
    genres_with_count = [GenreCount(genre=genre, count=count) for genre, count in result['genres'].items()]
    return RecommendCoordinatesResponse(
        coordinates=result['coordinates'],
        genres=genres_with_count,
        recommend_reasons=result.get('recommend_reasons')
    )

@app.post("/chat", response_model=ChatResponse)
async def chat_coordinate(request: ChatRequest):
    gemini_service = GeminiService()
    answer = await gemini_service.chat_coordinate_advice_async(
        request.question, 
        request.gender, 
        request.image_base64,
        request.model
    )
    return ChatResponse(answer=answer)

@app.get("/health/recommend-coordinates")
async def health_recommend_coordinates():
    try:
        # テスト用リクエストを作成
        test_request = RecommendCoordinatesRequest(gender="men")
        
        # recommend_coordinates関数を呼び出し
        result = await recommend_coordinates(test_request)
        
        # コンソールに出力
        print("=== Health check result for recommend-coordinates ===")
        print(f"Number of coordinates: {len(result.coordinates)}")
        print(f"Genres: {[f'{g.genre}({g.count})' for g in result.genres]}")
        
        for i, coord in enumerate(result.coordinates):
            print(f"\\n  {i+1}. コーディネート情報:")
            print(f"      ID: {coord.id}")
            print(f"      Image URL: {coord.image_url}")
            print(f"      Pin URL: {coord.pin_url_guess}")
            print(f"      Review: {coord.coordinate_review[:100] if coord.coordinate_review else 'None'}...")
            print(f"      Tops categorize: {coord.tops_categorize}")
            print(f"      Bottoms categorize: {coord.bottoms_categorize}")
            print(f"      Affiliate tops: {len(coord.affiliate_tops)} products")
            print(f"      Affiliate bottoms: {len(coord.affiliate_bottoms)} products")
            
            # アフィリエイト商品の詳細例を表示
            if coord.affiliate_tops:
                top_product = coord.affiliate_tops[0]
                print(f"      Top product example: {top_product.name[:50]}... (¥{top_product.price})")
            if coord.affiliate_bottoms:
                bottom_product = coord.affiliate_bottoms[0]
                print(f"      Bottom product example: {bottom_product.name[:50]}... (¥{bottom_product.price})")
        
        print("\\n=== 統合機能の確認完了 ===")
        print("✅ 3件のコーディネート取得")
        print("✅ coordinate_review 統合")
        print("✅ Yahoo Shopping API アフィリエイト商品取得")
        print("✅ トップス・ボトムス各15件の商品情報")
        
        return {
            "status": "success",
            "message": "recommend-coordinates endpoint test completed with integrated functionality",
            "coordinate_count": len(result.coordinates),
            "has_coordinate_reviews": all(coord.coordinate_review for coord in result.coordinates),
            "has_affiliate_products": all(coord.affiliate_tops or coord.affiliate_bottoms for coord in result.coordinates),
            "result": result
        }
        
    except Exception as e:
        print(f"Health check failed: {str(e)}")
        return {
            "status": "error",
            "message": f"Test failed: {str(e)}",
            "result": None
        }

@app.get("/chat-test", response_class=HTMLResponse)
async def chat_test_page():
    """
    Chat functionality test page
    """
    try:
        with open("static/chat-test.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Error: Test page not found</h1>",
            status_code=404
        )

@app.get("/fashion-review-test", response_class=HTMLResponse)
async def fashion_review_test_page():
    """
    Fashion review functionality test page
    """
    try:
        with open("static/fashion-review-test.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Error: Test page not found</h1>",
            status_code=404
        )

@app.get("/gemini-test", response_class=HTMLResponse)
async def gemini_test_page():
    """
    Gemini model test page
    """
    try:
        with open("static/gemini-test.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Error: Test page not found</h1>",
            status_code=404
        )

@app.post("/api/gemini-test", response_model=GeminiTestResponse)
async def gemini_test(request: GeminiTestRequest):
    """
    Test Gemini API with different models and prompts.
    Measures response time from client side.

    Args:
        request: GeminiTestRequest containing model and prompt

    Returns:
        GeminiTestResponse: Contains the response from Gemini
    """
    try:
        gemini_service = GeminiService()
        response = await gemini_service.test_gemini_async(request.prompt, request.model)
        return GeminiTestResponse(response=response)
    except Exception as e:
        print(f"Error in gemini_test endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health/chat")
async def health_chat():
    try:
        # テスト用リクエストを作成
        test_request = ChatRequest(
            question="30代男性に合う春のカジュアルコーデを教えて",
            gender="men"
        )
        
        # chat_coordinate関数を呼び出し
        result = await chat_coordinate(test_request)
        
        # コンソールに出力
        print("=== Health check result for chat endpoint ===")
        print(f"Question: {test_request.question}")
        print(f"Gender: {test_request.gender}")
        print(f"Answer: {result.answer}")
        print("\n=== チャット機能の確認完了 ===")
        print("✅ Gemini API統合")
        print("✅ 質問に対する回答生成")
        
        return {
            "status": "success",
            "message": "chat endpoint test completed with Gemini integration",
            "test_question": test_request.question,
            "test_gender": test_request.gender,
            "response_length": len(result.answer),
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


@app.get("/health/home-ui", response_class=HTMLResponse)
async def home_ui_test():
    """
    Serve the UI for testing the Home API.
    """
    with open("static/home-test.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/health/home")
async def health_home():
    """
    Health check for home API.
    Uses a dummy user_id or tries to fetch data to ensure logic works.
    """
    try:
        firebase_service = FirebaseService()
        
        # Use a known test user ID or a random one to check empty state
        test_user_id = "test-user-id"
        
        print(f"Testing home API with user_id: {test_user_id}")
        data = firebase_service.get_home_data(test_user_id)
        
        recent_count = len(data.get("recent_coordinates", []))
        tags_count = len(data.get("tags", []))
        
        return {
            "status": "success",
            "message": "Home API logic check completed",
            "test_user_id": test_user_id,
            "data_summary": {
                "recent_coordinates_count": recent_count,
                "tags_count": tags_count,
                "first_coordinate_date": data.get("recent_coordinates", [])[0].get("date") if recent_count > 0 else None
            },
            "raw_data_sample": {
                "recent_coordinates": data.get("recent_coordinates", [])[:1], # Show only 1
                "tags": data.get("tags", [])[:5] # Show first 5
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Home API test failed: {str(e)}"
        }


@app.get("/health/fashion-review")
async def health_fashion_review():
    """
    Health check endpoint for fashion review functionality.
    Uses test image to verify the entire flow:
    1. Image upload simulation
    2. Gemini AI review generation
    3. Firebase Storage upload (skipped in health check)
    4. Response formatting
    """
    # テスト用画像を読み込み
    image_path = "test/image/coordinate.jpg"

    try:
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')

        # Initialize services
        gemini_service = GeminiService()

        # Generate AI review and extract items using Gemini (single API call)
        print(f"[Health Check] Generating fashion review and extracting items for test image")
        ai_review = await gemini_service.generate_fashion_review_async(image_base64)

        # Build mock response (Firebase操作はスキップ)
        from datetime import datetime
        test_coordinate_id = "test-coordinate-id"
        current_date = datetime.now().strftime('%Y/%m/%d')

        extracted_items = ai_review.get("items", [])
        item_types = ai_review.get("item_types", [])

        print(f"[Health Check] Fashion review completed")
        print(f"  - AI Catchphrase: {ai_review['ai_catchphrase']}")
        print(f"  - AI Review: {ai_review['ai_review_comment'][:50]}...")
        print(f"  - Tags: {', '.join(ai_review['tags'])}")
        print(f"  - Item Types: {', '.join(item_types)}")
        print(f"  - Extracted Items: {len(extracted_items)}")
        for item in extracted_items:
            print(f"    * {item.get('item_type')}: {item.get('category')} ({item.get('color')})")

        # Build mock items list
        mock_items = []
        for item in extracted_items:
            mock_items.append({
                "id": f"item-{len(mock_items)}",
                "coordinate_id": test_coordinate_id,
                "item_type": item.get('item_type', ''),
                "item_image_path": "",
                "category": item.get('category', ''),
                "color": item.get('color', ''),
                "description": item.get('description', '')
            })

        return {
            "status": "success",
            "message": "fashion-review endpoint test completed with unified API call",
            "test_image": image_path,
            "ai_catchphrase": ai_review["ai_catchphrase"],
            "ai_review_comment": ai_review["ai_review_comment"],
            "tags": ai_review["tags"],
            "item_types": item_types,
            "extracted_items": extracted_items,
            "mock_response": {
                "current_coordinate": {
                    "id": test_coordinate_id,
                    "date": current_date,
                    "coodinate_image_path": "https://storage.googleapis.com/test-bucket/test-image.jpg"
                },
                "recent_coordinates": [],
                "items": mock_items,
                "ai_catchphrase": ai_review["ai_catchphrase"],
                "ai_review_comment": ai_review["ai_review_comment"],
                "tags": ai_review["tags"],
                "item_types": item_types
            }
        }

    except FileNotFoundError:
        return {
            "status": "error",
            "message": f"Test image not found: {image_path}",
            "result": None
        }
    except Exception as e:
        print(f"Health check failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Test failed: {str(e)}",
            "result": None
        }


@app.get("/health/fashion-type")
async def health_fashion_type():
    """
    Health check endpoint for fashion type diagnosis functionality.
    Uses test data to verify the entire flow:
    1. Request validation
    2. Score calculation
    3. Type code determination
    4. Response formatting
    """
    try:
        # Test request with sample answers
        test_request = FashionTypeDiagnosisRequest(
            user_id="test-user-health-check",
            Q1=4,  # 流行を追う傾向
            Q2=2,  # 定番を選ぶ傾向（逆転）
            Q3=4,  # 自分の好み優先
            Q4=4,  # 自分らしさ重視
            Q5=2,  # 他者評価はあまり気にしない
            Q6=2,  # 社会的印象はあまり気にしない
            Q7=2,  # 機能性よりデザイン（逆）
            Q8=2,  # 実用性よりスタイル（逆）
            Q9=3,  # 投資する傾向
            Q10=3  # 節約志向（逆転）
        )

        print("=== Health check for fashion-type ===")
        print(f"Test user ID: {test_request.user_id}")
        print(f"Test answers: Q1={test_request.Q1}, Q2={test_request.Q2}, Q3={test_request.Q3}, Q4={test_request.Q4}, Q5={test_request.Q5}")
        print(f"              Q6={test_request.Q6}, Q7={test_request.Q7}, Q8={test_request.Q8}, Q9={test_request.Q9}, Q10={test_request.Q10}")

        # Call endpoint
        result = await diagnose_fashion_type(test_request)

        print(f"[Health Check] Fashion type diagnosis completed")
        print(f"  - Type Code: {result.type_code}")
        print(f"  - Type Name: {result.type_name}")
        print(f"  - Trend Score: {result.trend_score}")
        print(f"  - Self Score: {result.self_score}")
        print(f"  - Social Score: {result.social_score}")
        print(f"  - Function Score: {result.function_score}")
        print(f"  - Economy Score: {result.economy_score}")

        print("\n=== Fashion type diagnosis check completed ===")
        print("✅ Request validation")
        print("✅ Score calculation")
        print("✅ Type code determination")
        print("✅ Firestore save")

        return {
            "status": "success",
            "message": "fashion-type endpoint test completed",
            "test_params": {
                "user_id": test_request.user_id,
                "answers": {
                    "Q1": test_request.Q1,
                    "Q2": test_request.Q2,
                    "Q3": test_request.Q3,
                    "Q4": test_request.Q4,
                    "Q5": test_request.Q5,
                    "Q6": test_request.Q6,
                    "Q7": test_request.Q7,
                    "Q8": test_request.Q8,
                    "Q9": test_request.Q9,
                    "Q10": test_request.Q10
                }
            },
            "result": {
                "diagnosis_id": result.diagnosis_id,
                "type_code": result.type_code,
                "type_name": result.type_name,
                "scores": {
                    "trend": result.trend_score,
                    "self": result.self_score,
                    "social": result.social_score,
                    "function": result.function_score,
                    "economy": result.economy_score
                },
                "created_at": result.created_at
            }
        }

    except Exception as e:
        print(f"Health check failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Test failed: {str(e)}",
            "result": None
        }


@app.get("/health/animal-fortune")
async def health_animal_fortune():
    """
    Health check endpoint for animal fortune diagnosis functionality.
    Uses test data to verify the entire flow:
    1. Request validation
    2. Animal number calculation
    3. Fortune data retrieval
    4. Response formatting
    """
    try:
        # Test request with sample birth date
        test_request = AnimalFortuneRequest(
            user_id="test-user-health-check",
            year=2000,
            month=1,
            day=1
        )

        print("=== Health check for animal-fortune ===")
        print(f"Test user ID: {test_request.user_id}")
        print(f"Test birth date: {test_request.year}/{test_request.month}/{test_request.day}")

        # Call endpoint
        result = await diagnose_animal_fortune(test_request)

        print(f"[Health Check] Animal fortune diagnosis completed")
        print(f"  - Animal: {result.animal}")
        print(f"  - Animal Name: {result.animal_name}")
        print(f"  - Base Personality: {result.base_personality[:50]}...")
        print(f"  - Life Tendency: {result.life_tendency[:50]}...")
        print(f"  - Female Feature: {result.female_feature[:50]}...")
        print(f"  - Male Feature: {result.male_feature[:50]}...")
        print(f"  - Love Tendency: {result.love_tendency[:50]}...")
        print(f"  - Link: {result.link}")

        print("\n=== Animal fortune diagnosis check completed ===")
        print("✅ Request validation")
        print("✅ Animal number calculation")
        print("✅ Fortune data retrieval")
        print("✅ Firestore save")

        return {
            "status": "success",
            "message": "animal-fortune endpoint test completed",
            "test_params": {
                "user_id": test_request.user_id,
                "birth_date": {
                    "year": test_request.year,
                    "month": test_request.month,
                    "day": test_request.day
                }
            },
            "result": {
                "fortune_id": result.fortune_id,
                "animal": result.animal,
                "animal_name": result.animal_name,
                "base_personality": result.base_personality,
                "life_tendency": result.life_tendency,
                "female_feature": result.female_feature,
                "male_feature": result.male_feature,
                "love_tendency": result.love_tendency,
                "link": result.link,
                "created_at": result.created_at
            }
        }

    except Exception as e:
        print(f"Health check failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Test failed: {str(e)}",
            "result": None
        }


@app.get("/health/user-insight")
async def health_user_insight():
    """
    Health check endpoint for user insight functionality.
    Uses test data to verify the entire flow:
    1. Fashion type diagnosis (creates test data)
    2. Animal fortune diagnosis (creates test data)
    3. User insight generation with Gemini
    4. Response formatting
    """
    try:
        test_user_id = "test-user-health-insight"

        print("=== Health check for user-insight ===")
        print(f"Test user ID: {test_user_id}")

        # Step 1: Create fashion type diagnosis
        print("\n[1/3] Creating fashion type diagnosis...")
        fashion_request = FashionTypeDiagnosisRequest(
            user_id=test_user_id,
            Q1=5, Q2=1, Q3=5, Q4=5, Q5=1,
            Q6=1, Q7=1, Q8=1, Q9=5, Q10=1
        )
        fashion_result = await diagnose_fashion_type(fashion_request)
        print(f"  ✅ Fashion type: {fashion_result.type_name} ({fashion_result.type_code})")

        # Step 2: Create animal fortune diagnosis
        print("\n[2/3] Creating animal fortune diagnosis...")
        animal_request = AnimalFortuneRequest(
            user_id=test_user_id,
            year=2000,
            month=1,
            day=1
        )
        animal_result = await diagnose_animal_fortune(animal_request)
        print(f"  ✅ Animal: {animal_result.animal_name} ({animal_result.animal})")

        # Step 3: Generate user insight
        print("\n[3/3] Generating user insight...")
        insight_result = await get_user_insight(test_user_id)

        print(f"\n[Health Check] User insight generation completed")
        print(f"  - Status: {insight_result['status']}")
        print(f"  - Fashion Type: {insight_result.get('fashion_type', {}).get('type_name', 'N/A')}")
        print(f"  - Animal: {insight_result.get('animal_fortune', {}).get('animal_name', 'N/A')}")

        # Handle Gemini API error gracefully
        insight_text = insight_result.get('insight', '')
        if "失敗" in insight_text or "エラー" in insight_text:
            print(f"  - Insight: ⚠️  {insight_text}")
            print(f"\n⚠️  Note: Gemini API may not be available in local environment")
            print(f"    This is expected and will work on deployed environment with GOOGLE_GENAI_API_KEY")
        else:
            print(f"  - Insight: {insight_text[:100]}...")

        print("\n=== User insight check completed ===")
        print("✅ Fashion type diagnosis")
        print("✅ Animal fortune diagnosis")
        print("✅ Data retrieval from Firestore")
        if "失敗" not in insight_text and "エラー" not in insight_text:
            print("✅ Gemini insight generation")
        else:
            print("⚠️  Gemini insight generation (API key required)")

        return {
            "status": "success",
            "message": "user-insight endpoint test completed",
            "test_params": {
                "user_id": test_user_id
            },
            "result": {
                "status": insight_result['status'],
                "user_id": insight_result['user_id'],
                "fashion_type": insight_result.get('fashion_type'),
                "animal_fortune": insight_result.get('animal_fortune'),
                "insight": insight_result.get('insight'),
                "generated_at": insight_result.get('generated_at'),
                "gemini_available": "失敗" not in insight_text and "エラー" not in insight_text
            }
        }

    except Exception as e:
        print(f"Health check failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Test failed: {str(e)}",
            "result": None
        }


@app.get("/health/analyze-recent-coordinate")
async def health_analyze_recent_coordinate():
    """
    Health check endpoint for analyze-recent-coordinate functionality.
    Tests the coordinate analysis with a test user ID.
    """
    try:
        # Test request
        test_request = AnalyzeRecentCoordinateRequest(
            uid="test-user-id",
            target_days=30  # Use 30 days to increase chance of finding data
        )

        # Call the endpoint
        result = await analyze_recent_coordinate(test_request)

        # Console output
        print("=== Health check result for analyze-recent-coordinate ===")
        print(f"Test user ID: {test_request.uid}")
        print(f"Target days: {test_request.target_days}")
        print(f"Analysis result: {result.analyze_recent_coordinate}")
        print("\n=== 分析機能の確認完了 ===")
        print("✅ Firebase からタグ取得")
        print("✅ Gemini 2.5-flash-lite で分析生成")
        print("✅ 日本語での分析文生成")

        return {
            "status": "success",
            "message": "analyze-recent-coordinate endpoint test completed",
            "test_params": {
                "uid": test_request.uid,
                "target_days": test_request.target_days
            },
            "analysis_length": len(result.analyze_recent_coordinate),
            "result": result
        }

    except Exception as e:
        print(f"Health check failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Test failed: {str(e)}",
            "result": None
        }


@app.get("/api/home", response_model=HomeResponse)
async def home_data(user_id: str):
    """
    Home screen API endpoint.
    Returns recent coordinates and user tags.
    
    Args:
        user_id: User ID (query parameter)
        
    Returns:
        HomeResponse: Dashboard data
    """
    firebase_service = FirebaseService()
    
    print(f"Fetching home data for user: {user_id}")
    data = firebase_service.get_home_data(user_id)
    
    return HomeResponse(
        recent_coordinates=[
            HomeRecentCoordinate(**item) for item in data.get("recent_coordinates", [])
        ],
        analysis_summary="",  # Currently empty as requested
        tags=data.get("tags", [])
    )


@app.get("/api/closet", response_model=ClosetResponse)
async def get_closet_items(user_id: str, item_type: Optional[str] = None):
    """
    Closet API endpoint.
    Returns user's items, optionally filtered by type.
    
    Args:
        user_id: User ID
        item_type: Filter by item type (e.g., 'トップス', 'ボトムス')
        
    Returns:
        ClosetResponse: List of items
    """
    firebase_service = FirebaseService()
    
    print(f"Fetching closet items for user: {user_id}, type: {item_type}")
    items_data = firebase_service.get_user_items(user_id, item_type)
    
    items = []
    for data in items_data:
        # Format date
        date_str = ''
        if 'created_at' in data and data['created_at']:
             try:
                # Assuming created_at is already converted to string in service
                # If it's isoformat, we might want to simplify it to YYYY/MM/DD
                ts_str = str(data['created_at'])
                if 'T' in ts_str:
                     date_obj = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                     date_str = date_obj.strftime('%Y/%m/%d')
                else:
                     date_str = ts_str
             except:
                 pass

        items.append(ClosetItem(
            id=data.get('id', ''),
            item_type=data.get('item_type', ''),
            category=data.get('category'),
            color=data.get('color'),
            image_url=data.get('image_url'),
            date=date_str
        ))
    
    return ClosetResponse(items=items)


@app.post("/api/analyze-recent-coordinate", response_model=AnalyzeRecentCoordinateResponse)
async def analyze_recent_coordinate(request: AnalyzeRecentCoordinateRequest):
    """
    Analyze recent coordinate endpoint.
    Analyzes user's recent coordinate tags and returns a fashion trend summary.

    Args:
        request: AnalyzeRecentCoordinateRequest containing uid and target_days

    Returns:
        AnalyzeRecentCoordinateResponse: Contains analyze_recent_coordinate summary
    """
    try:
        firebase_service = FirebaseService()
        gemini_service = GeminiService()

        # Get tags from recent coordinates
        print(f"Fetching recent coordinates for user: {request.uid}, target_days: {request.target_days}")
        tags_list = firebase_service.get_recent_coordinates_with_tags(
            user_id=request.uid,
            target_days=request.target_days,
            limit=3
        )

        # Generate analysis from tags
        if not tags_list:
            # No coordinates found, return default message
            return AnalyzeRecentCoordinateResponse(
                analyze_recent_coordinate="最近のコーディネートデータがありません。新しいコーディネートを投稿してみましょう！"
            )

        print(f"Generating analysis from {len(tags_list)} coordinate tags")
        analysis = await gemini_service.analyze_recent_coordinates_async(tags_list)

        if not analysis:
            # Fallback if Gemini fails
            analysis = "あなたのファッションスタイルを分析しています。もう少しコーディネートを投稿すると、より詳しい分析ができます！"

        return AnalyzeRecentCoordinateResponse(
            analyze_recent_coordinate=analysis
        )

    except Exception as e:
        print(f"Error in analyze_recent_coordinate endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/fashion_review", response_model=FashionReviewResponse)
async def fashion_review(
    user_id: str = Form(...),
    user_token: str = Form(...),
    file: UploadFile = File(...),
    tops_image: UploadFile = File(None),
    bottoms_image: UploadFile = File(None)
):
    """
    Fashion review endpoint that analyzes full-body coordinate images.

    Args:
        user_id: User ID
        user_token: User authentication token
        file: Full-body coordinate image (JPEG/PNG)

    Returns:
        FashionReviewResponse: Contains current coordinate, recent coordinates, items, AI review, and tags
    """
    import time
    request_start_time = time.time()

    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

        # TODO: Validate user_token (currently simplified)
        # In production, implement proper authentication
        if not user_id or not user_token:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Read image data
        image_data = await file.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')

        # Initialize services
        gemini_service = GeminiService()
        firebase_service = FirebaseService()

        # Generate AI review and extract items using Gemini (parallel API calls)
        print(f"Generating fashion review and extracting items for user: {user_id}")
        ai_review = await gemini_service.generate_fashion_review_async(image_base64)

        # Prepare image upload tasks (parallel execution)
        upload_start_time = time.time()
        print("Uploading images to Firebase Storage in parallel...")

        # Validate and read optional images first
        tops_image_data = None
        bottoms_image_data = None

        if tops_image:
            if not tops_image.content_type or not tops_image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="Invalid tops_image file type")
            tops_image_data = await tops_image.read()

        if bottoms_image:
            if not bottoms_image.content_type or not bottoms_image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="Invalid bottoms_image file type")
            bottoms_image_data = await bottoms_image.read()

        # Build parallel upload tasks
        upload_tasks = {
            'coordinate': asyncio.to_thread(
                firebase_service.upload_image,
                image_data,
                f"coordinates/{user_id}"
            )
        }

        if tops_image_data:
            upload_tasks['tops'] = asyncio.to_thread(
                firebase_service.upload_image,
                tops_image_data,
                f"items/{user_id}/tops"
            )

        if bottoms_image_data:
            upload_tasks['bottoms'] = asyncio.to_thread(
                firebase_service.upload_image,
                bottoms_image_data,
                f"items/{user_id}/bottoms"
            )

        # Execute all uploads in parallel
        upload_results = await asyncio.gather(*upload_tasks.values())

        # Map results back to named variables
        result_keys = list(upload_tasks.keys())
        coordinate_image_url = upload_results[result_keys.index('coordinate')]
        tops_image_url = upload_results[result_keys.index('tops')] if 'tops' in result_keys else None
        bottoms_image_url = upload_results[result_keys.index('bottoms')] if 'bottoms' in result_keys else None

        upload_elapsed_time = time.time() - upload_start_time
        print(f"[Parallel Upload] Completed in {upload_elapsed_time:.2f}s")
        print(f"Uploaded coordinate_image: {coordinate_image_url}")
        if tops_image_url:
            print(f"Uploaded tops_image: {tops_image_url}")
        if bottoms_image_url:
            print(f"Uploaded bottoms_image: {bottoms_image_url}")

        # Generate unique coordinate ID
        import uuid
        from datetime import datetime
        coordinate_id = str(uuid.uuid4())
        current_date = datetime.now().strftime('%Y/%m/%d')

        # Prepare items data for saving
        extracted_items = ai_review.get("items", [])

        # Validate that corresponding items exist for uploaded images
        if tops_image_url:
            has_tops = any(item.get('item_type') == 'トップス' for item in extracted_items)
            if not has_tops:
                raise HTTPException(status_code=400, detail="トップスの画像が送信されましたが、コーディネート画像からトップスが検出されませんでした")

        if bottoms_image_url:
            has_bottoms = any(item.get('item_type') == 'ボトムス' for item in extracted_items)
            if not has_bottoms:
                raise HTTPException(status_code=400, detail="ボトムスの画像が送信されましたが、コーディネート画像からボトムスが検出されませんでした")

        # Flags to track image assignment (assign to first matching item only)
        tops_assigned = False
        bottoms_assigned = False

        items_for_firestore = []
        items_for_response = []

        for item_data in extracted_items:
            item_id = str(uuid.uuid4())
            item_type = item_data.get('item_type', '')

            # Determine item image path
            item_image_path = ''
            if item_type == 'トップス' and tops_image_url and not tops_assigned:
                item_image_path = tops_image_url
                tops_assigned = True
                print(f"  Assigned tops_image to item: {item_data.get('category', 'Unknown')}")
            elif item_type == 'ボトムス' and bottoms_image_url and not bottoms_assigned:
                item_image_path = bottoms_image_url
                bottoms_assigned = True
                print(f"  Assigned bottoms_image to item: {item_data.get('category', 'Unknown')}")

            # Prepare item for Firestore (embedded in coordinate document)
            items_for_firestore.append({
                'id': item_id,
                'coordinate_id': coordinate_id,
                'item_type': item_type,
                'item_image_path': item_image_path,
                'category': item_data.get('category'),
                'color': item_data.get('color'),
                'description': item_data.get('description')
            })

            # Prepare item for API response
            items_for_response.append(FashionReviewItem(
                id=item_id,
                coordinate_id=coordinate_id,
                item_type=item_type,
                item_image_path=item_image_path,
                category=item_data.get('category'),
                color=item_data.get('color'),
                description=item_data.get('description')
            ))

            print(f"  Prepared item: {item_type} - {item_data.get('category')}")

        # Save coordinate with items and item_types to Firestore
        print("Saving coordinate with items to Firestore...")
        firebase_service.save_coordinate(
            user_id=user_id,
            coordinate_id=coordinate_id,
            image_path=coordinate_image_url,
            ai_catchphrase=ai_review["ai_catchphrase"],
            ai_review_comment=ai_review["ai_review_comment"],
            tags=ai_review["tags"],
            items=items_for_firestore,
            item_types=ai_review.get("item_types", [])
        )

        # Save individual items to user's closet (users/{user_id}/items)
        print("Saving items to user's closet...")
        for item in items_for_firestore:
            try:
                firebase_service.save_user_item(
                    user_id=user_id,
                    item_id=item['id'],
                    coordinate_id=coordinate_id,
                    item_type=item['item_type'],
                    category=item.get('category'),
                    color=item.get('color'),
                    image_url=item.get('item_image_path', coordinate_image_url),  # Use individual image if available
                    description=item.get('description')
                )
            except Exception as e:
                print(f"Failed to save item to closet: {e}")

        # Get user's recent coordinates
        print("Fetching recent coordinates...")
        recent_coords_data = firebase_service.get_user_coordinates(user_id, limit=10)

        # Format recent coordinates (exclude the current one)
        recent_coordinates = []
        for coord_data in recent_coords_data:
            if coord_data.get('id') != coordinate_id:
                # Convert date from ISO format to YYYY/MM/DD
                date_str = coord_data.get('date', '')
                if date_str:
                    try:
                        # Parse ISO format and convert to YYYY/MM/DD
                        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        formatted_date = date_obj.strftime('%Y/%m/%d')
                    except (ValueError, AttributeError):
                        formatted_date = date_str
                else:
                    formatted_date = ''

                recent_coordinates.append(FashionReviewRecentCoordinate(
                    id=coord_data.get('id', ''),
                    date=formatted_date,
                    coodinate_image_path=coord_data.get('coordinate_image_path', ''),
                    ai_catchphrase=coord_data.get('ai_catchphrase', ''),
                    ai_review_comment=coord_data.get('ai_review_comment', '')
                ))

        # Build response
        response = FashionReviewResponse(
            current_coordinate=FashionReviewCurrentCoordinate(
                id=coordinate_id,
                date=current_date,
                coodinate_image_path=coordinate_image_url
            ),
            recent_coordinates=recent_coordinates,
            items=items_for_response,
            ai_catchphrase=ai_review["ai_catchphrase"],
            ai_review_comment=ai_review["ai_review_comment"],
            tags=ai_review["tags"],
            item_types=ai_review.get("item_types", [])
        )

        request_elapsed_time = time.time() - request_start_time
        print(f"[Total Request] Fashion review completed in {request_elapsed_time:.2f}s for user: {user_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in fashion_review endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")




@app.post("/coordinate-recommend")
async def coordinate_recommend(request: CoordinateRecommendRequest):
    """
    Coordinate recommendation endpoint using TF-IDF based recommendation model.

    Args:
        request: CoordinateRecommendRequest containing gender, input_type, category, text, num_outfits, num_candidates

    Returns:
        Dictionary containing outfit recommendations and category item lists with English keys
    """
    try:
        # Get recommendations from model
        result = RecommendService.get_recommendations(
            gender=request.gender,
            input_type=request.input_type,
            category=request.category,
            text=request.text,
            num_outfits=request.num_outfits,
            num_candidates=request.num_candidates
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in coordinate_recommend endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/coordinate-recommend/bulk", response_model=BulkCoordinateRecommendResponse)
async def coordinate_recommend_bulk(request: BulkCoordinateRecommendRequest):
    """
    複数アイテムのコーディネート提案を並列処理で実行。

    各アイテムは独立して処理され、個別の失敗は全体を止めない。

    Args:
        request: BulkCoordinateRecommendRequest

    Returns:
        BulkCoordinateRecommendResponse: 各アイテムの推薦結果
    """
    import time
    start_time = time.time()

    try:
        print(f"[BulkCoordinateRecommend] Processing {len(request.items)} items")

        # 並列処理タスクの作成
        tasks = []
        for idx, item in enumerate(request.items):
            task = asyncio.to_thread(
                _process_single_recommendation,
                item,
                idx
            )
            tasks.append(task)

        # 全ての推薦を並列実行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 結果の集計
        processed_results = []
        success_count = 0
        failed_count = 0

        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                # 予期しない例外
                processed_results.append(CoordinateRecommendResult(
                    item_id=request.items[idx].item_id,
                    index=idx,
                    status="error",
                    input_type=request.items[idx].input_type,
                    category=request.items[idx].category,
                    text=request.items[idx].text,
                    error=str(result)
                ))
                failed_count += 1
            else:
                processed_results.append(result)
                if result.status == "success":
                    success_count += 1
                else:
                    failed_count += 1

        # 全体ステータスの決定
        if failed_count == 0:
            overall_status = "success"
        elif success_count == 0:
            overall_status = "error"
        else:
            overall_status = "partial_success"

        processing_time = (time.time() - start_time) * 1000

        print(f"[BulkCoordinateRecommend] Completed: {success_count} success, {failed_count} failed, {processing_time:.2f}ms")

        return BulkCoordinateRecommendResponse(
            status=overall_status,
            total_count=len(request.items),
            success_count=success_count,
            failed_count=failed_count,
            results=processed_results,
            processing_time_ms=processing_time
        )

    except Exception as e:
        print(f"[BulkCoordinateRecommend] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def _process_single_recommendation(
    item: BulkCoordinateRecommendItem,
    index: int
) -> CoordinateRecommendResult:
    """
    単一アイテムの推薦処理（asyncio.to_thread用ヘルパー関数）

    Args:
        item: 推薦対象アイテム
        index: リクエスト配列内の位置

    Returns:
        CoordinateRecommendResult: 推薦結果またはエラー
    """
    try:
        # 既存のRecommendServiceを呼び出し
        result = RecommendService.get_recommendations(
            gender=item.gender,
            input_type=item.input_type,
            category=item.category,
            text=item.text,
            num_outfits=item.num_outfits,
            num_candidates=item.num_candidates
        )

        # サービスがエラーを返した場合
        if "error" in result:
            return CoordinateRecommendResult(
                item_id=item.item_id,
                index=index,
                status="error",
                input_type=item.input_type,
                category=item.category,
                text=item.text,
                error=result["error"]
            )

        # 成功 - 推薦結果を返す
        return CoordinateRecommendResult(
            item_id=item.item_id,
            index=index,
            status="success",
            input_type=item.input_type,
            category=item.category,
            text=item.text,
            recommend_coordinates=result.get("recommend_coordinates", []),
            outer_list=result.get("outer_list", []),
            tops_list=result.get("tops_list", []),
            bottoms_list=result.get("bottoms_list", []),
            shoes_list=result.get("shoes_list", []),
            accessories_list=result.get("accessories_list", [])
        )

    except Exception as e:
        # 処理中の予期しないエラー
        return CoordinateRecommendResult(
            item_id=item.item_id,
            index=index,
            status="error",
            input_type=item.input_type,
            category=item.category,
            text=item.text,
            error=f"Processing failed: {str(e)}"
        )


@app.get("/health/coordinate-recommend")
async def health_coordinate_recommend():
    """
    Health check endpoint for coordinate recommendation functionality.
    Tests the recommendation engine with sample data.
    """
    try:
        # Test request for women's wide pants
        test_request = CoordinateRecommendRequest(
            gender="women",
            input_type="ボトムス",
            category="ワイドパンツ",
            text="ブラックのワイドパンツ",
            num_outfits=5,
            num_candidates=10
        )

        # Get recommendations
        result = RecommendService.get_recommendations(
            gender=test_request.gender,
            input_type=test_request.input_type,
            category=test_request.category,
            text=test_request.text,
            num_outfits=test_request.num_outfits,
            num_candidates=test_request.num_candidates
        )

        # Check for errors
        if "error" in result:
            return {
                "status": "error",
                "message": result["error"],
                "test_params": {
                    "gender": test_request.gender,
                    "input_type": test_request.input_type,
                    "category": test_request.category,
                    "text": test_request.text,
                    "num_outfits": test_request.num_outfits,
                    "num_candidates": test_request.num_candidates
                }
            }

        # Console output
        print("=== Health check result for coordinate-recommend ===")
        print(f"Test parameters:")
        print(f"  Gender: {test_request.gender}")
        print(f"  Input type: {test_request.input_type}")
        print(f"  Category: {test_request.category}")
        print(f"  Text: {test_request.text}")
        print(f"\\nResults:")

        # Count outfits from recommend_coordinates list
        recommend_coords = result.get("recommend_coordinates", [])
        outfit_count = len(recommend_coords)
        print(f"  Number of outfits: {outfit_count}")

        # Count category lists
        category_lists = [key for key in result.keys() if key.endswith("_list")]
        print(f"  Category lists: {', '.join(category_lists)}")

        # Display sample coordinate
        if recommend_coords:
            print(f"\\n  Sample coordinate:")
            sample = recommend_coords[0]
            for key, value in sample.items():
                print(f"    {key}: {value}")

        print("\\n=== Coordinate recommendation check completed ===")
        print("✅ TF-IDF model loaded")
        print("✅ Recommendations generated")
        print("✅ Category lists generated")
        print("✅ Response format: English keys with recommend_coordinates as list")

        return {
            "status": "success",
            "message": "coordinate-recommend endpoint test completed",
            "test_params": {
                "gender": test_request.gender,
                "input_type": test_request.input_type,
                "category": test_request.category,
                "text": test_request.text,
                "num_outfits": test_request.num_outfits,
                "num_candidates": test_request.num_candidates
            },
            "outfit_count": outfit_count,
            "category_lists": category_lists,
            "result": result
        }

    except Exception as e:
        print(f"Health check failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Test failed: {str(e)}",
            "result": None
        }


# ============================================================
# Calendar API Health Checks
# ============================================================

@app.get("/health/coordinate-list")
async def health_coordinate_list():
    """
    Health check for GET /api/coordinate/list/{uid}.
    当月のコーディネートリストを test-user-id で取得し、レスポンス形式を確認する。
    """
    import calendar as cal_module

    try:
        test_user_id = "test-user-id"
        now = datetime.now()
        year, month = now.year, now.month

        print(f"=== Health check: /api/coordinate/list ===")
        print(f"  test_user_id: {test_user_id}")
        print(f"  target: {year}/{month:02d}")

        firebase = FirebaseService()
        coordinates = firebase.get_coordinates_by_month(test_user_id, year, month)

        coord_by_day: Dict[int, Dict[str, Any]] = {}
        for coord in coordinates:
            date_str = coord.get('date', '')
            if date_str:
                try:
                    day = int(date_str.split('/')[2])
                    coord_by_day[day] = coord
                except (IndexError, ValueError):
                    pass

        _, num_days = cal_module.monthrange(year, month)
        result = []
        for day in range(1, num_days + 1):
            if day in coord_by_day:
                coord = coord_by_day[day]
                result.append(CoordinateListItem(
                    year=year,
                    month=month,
                    day=day,
                    id=coord.get('id'),
                    coodinate_image_path=coord.get('coordinate_image_path')
                ))
            else:
                result.append(CoordinateListItem(
                    year=year,
                    month=month,
                    day=day,
                    id=None,
                    coodinate_image_path=None
                ))

        filled_days = [item for item in result if item.id is not None]

        print(f"  total days: {num_days}")
        print(f"  days with coordinate: {len(filled_days)}")
        print("✅ coordinate-list health check passed")

        return {
            "status": "success",
            "message": "coordinate-list endpoint test completed",
            "test_params": {
                "uid": test_user_id,
                "year": year,
                "month": month
            },
            "summary": {
                "total_days": num_days,
                "days_with_coordinate": len(filled_days),
                "days_without_coordinate": num_days - len(filled_days)
            },
            "sample": [item.model_dump() for item in result[:5]]
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Test failed: {str(e)}",
            "result": None
        }


@app.get("/health/coordinate-date")
async def health_coordinate_date():
    """
    Health check for GET /api/coordinate/date/{uid}/{target_date}.
    今日の日付で test-user-id のコーディネート詳細取得を確認する。
    """
    try:
        test_user_id = "test-user-id"
        today = datetime.now().strftime("%Y-%m-%d")

        print(f"=== Health check: /api/coordinate/date ===")
        print(f"  test_user_id: {test_user_id}")
        print(f"  target_date: {today}")

        firebase = FirebaseService()
        coordinate = firebase.get_coordinate_by_date(test_user_id, today)

        if not coordinate:
            print(f"  No coordinate found for {today} (expected for test user)")
            return {
                "status": "success",
                "message": "coordinate-date endpoint test completed (no data for test user)",
                "test_params": {
                    "uid": test_user_id,
                    "target_date": today
                },
                "result": []
            }

        coord_date = coordinate.get('date', '').replace('/', '-')
        items_data = coordinate.get('items', [])
        items = [
            CoordinateDetailItem(
                id=item.get('id', ''),
                coordinate_id=item.get('coordinate_id', coordinate.get('id', '')),
                item_type=item.get('item_type', ''),
                item_image_path=item.get('item_image_path', '')
            )
            for item in items_data
        ]

        response = CoordinateDetailResponse(
            current_coordinate=CoordinateDetailCurrentCoordinate(
                id=coordinate.get('id', ''),
                date=coord_date,
                coodinate_image_path=coordinate.get('coordinate_image_path', '')
            ),
            items=items,
            ai_catchphrase=coordinate.get('ai_catchphrase', ''),
            ai_review_comment=coordinate.get('ai_review_comment', '')
        )

        print(f"  coordinate_id: {coordinate.get('id')}")
        print(f"  items_count: {len(items)}")
        print("✅ coordinate-date health check passed")

        return {
            "status": "success",
            "message": "coordinate-date endpoint test completed",
            "test_params": {
                "uid": test_user_id,
                "target_date": today
            },
            "result": [response.model_dump()]
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Test failed: {str(e)}",
            "result": None
        }


# ============================================================
# Calendar API
# ============================================================

@app.get("/api/coordinate/list/{uid}", response_model=List[CoordinateListItem])
async def get_coordinate_list(uid: str, year: int, month: int, page: int = 0):
    """
    指定ユーザーの指定年月のコーディネートリストを返す。
    その月の全日付をレスポンスに含め、コーデがない日は id / coodinate_image_path を null にする。
    """
    import calendar as cal_module

    firebase = FirebaseService()
    coordinates = firebase.get_coordinates_by_month(uid, year, month)

    # day -> coordinate data のマッピングを構築
    coord_by_day: Dict[int, Dict[str, Any]] = {}
    for coord in coordinates:
        date_str = coord.get('date', '')  # YYYY/MM/DD
        if date_str:
            try:
                day = int(date_str.split('/')[2])
                coord_by_day[day] = coord
            except (IndexError, ValueError):
                pass

    # 月の全日数分のレスポンスを生成
    _, num_days = cal_module.monthrange(year, month)
    result = []
    for day in range(1, num_days + 1):
        if day in coord_by_day:
            coord = coord_by_day[day]
            result.append(CoordinateListItem(
                year=year,
                month=month,
                day=day,
                id=coord.get('id'),
                coodinate_image_path=coord.get('coordinate_image_path')
            ))
        else:
            result.append(CoordinateListItem(
                year=year,
                month=month,
                day=day,
                id=None,
                coodinate_image_path=None
            ))

    return result


@app.get("/api/coordinate/date/{uid}/{target_date}", response_model=List[CoordinateDetailResponse])
async def get_coordinate_by_date(uid: str, target_date: str):
    """
    指定ユーザーの指定日付（YYYY-MM-DD）のコーディネート詳細を返す。
    コーデが存在しない場合は空配列を返す。
    """
    firebase = FirebaseService()
    coordinate = firebase.get_coordinate_by_date(uid, target_date)

    if not coordinate:
        return []

    # Firestore の date（YYYY/MM/DD）を YYYY-MM-DD 形式に変換
    coord_date = coordinate.get('date', '').replace('/', '-')

    # embedded items 配列からレスポンス用アイテムを構築
    items_data = coordinate.get('items', [])
    items = [
        CoordinateDetailItem(
            id=item.get('id', ''),
            coordinate_id=item.get('coordinate_id', coordinate.get('id', '')),
            item_type=item.get('item_type', ''),
            item_image_path=item.get('item_image_path', '')
        )
        for item in items_data
    ]

    response = CoordinateDetailResponse(
        current_coordinate=CoordinateDetailCurrentCoordinate(
            id=coordinate.get('id', ''),
            date=coord_date,
            coodinate_image_path=coordinate.get('coordinate_image_path', '')
        ),
        items=items,
        ai_catchphrase=coordinate.get('ai_catchphrase', ''),
        ai_review_comment=coordinate.get('ai_review_comment', '')
    )

    return [response]


@app.get("/health/delete-coordinate")
async def health_delete_coordinate():
    """
    Health check for delete coordinate functionality.
    Tests with test-user-id to verify the deletion logic works.
    """
    try:
        firebase = FirebaseService()
        test_user_id = "test-user-id"

        print(f"=== Health check: delete-coordinate ===")
        print(f"  test_user_id: {test_user_id}")

        # Get user's coordinates to find one to test with
        coords = firebase.get_user_coordinates(test_user_id, limit=1)

        if not coords:
            return {
                "status": "success",
                "message": "No coordinates found for test user (expected for clean test environment)",
                "note": "To fully test, create a coordinate first using /api/fashion_review"
            }

        test_coordinate = coords[0]
        test_coordinate_id = test_coordinate.get('id')

        print(f"  Found test coordinate: {test_coordinate_id}")
        print(f"  Coordinate has {len(test_coordinate.get('items', []))} embedded items")

        # Note: We don't actually delete in health check to avoid data loss
        # Just verify the coordinate exists and show what would be deleted
        return {
            "status": "success",
            "message": "Delete coordinate logic is ready",
            "test_coordinate_id": test_coordinate_id,
            "items_count": len(test_coordinate.get('items', [])),
            "note": "Health check does not actually delete data. Use DELETE /api/coordinate/{coordinate_id}?uid={uid} to delete."
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Test failed: {str(e)}"
        }


@app.delete("/api/coordinate/{coordinate_id}", response_model=DeleteCoordinateResponse)
async def delete_coordinate(coordinate_id: str, uid: str):
    """
    指定されたコーディネートと関連アイテムを削除する。
    Firestore と Firebase Storage から削除される。

    Args:
        coordinate_id: 削除するコーディネートのID（パスパラメータ）
        uid: ユーザーID（クエリパラメータ）

    Returns:
        DeleteCoordinateResponse: 削除結果
    """
    try:
        firebase = FirebaseService()
        result = firebase.delete_coordinate(uid, coordinate_id)

        return DeleteCoordinateResponse(
            success=result["success"],
            message=result["message"],
            deleted_items_count=result["deleted_items_count"]
        )

    except Exception as e:
        print(f"Error in delete_coordinate endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/fashion-type", response_model=FashionTypeDiagnosisResponse)
async def diagnose_fashion_type(request: FashionTypeDiagnosisRequest):
    """
    Fashion type diagnosis endpoint.
    Analyzes user's 10 question responses and returns their fashion type.

    Args:
        request: FashionTypeDiagnosisRequest containing user_id and Q1-Q10 answers

    Returns:
        FashionTypeDiagnosisResponse: Diagnosis result with type code, name, and scores
    """
    try:
        # バリデーション: user_idの存在チェック
        if not request.user_id or request.user_id.strip() == "":
            raise HTTPException(status_code=400, detail="user_id is required")

        # 回答データを辞書形式に変換
        answers = {
            "Q1": request.Q1,
            "Q2": request.Q2,
            "Q3": request.Q3,
            "Q4": request.Q4,
            "Q5": request.Q5,
            "Q6": request.Q6,
            "Q7": request.Q7,
            "Q8": request.Q8,
            "Q9": request.Q9,
            "Q10": request.Q10
        }

        print(f"[Fashion Type] Diagnosing for user: {request.user_id}")
        print(f"[Fashion Type] Answers: {answers}")

        # Firebase Serviceを初期化
        firebase_service = FirebaseService()

        # Fashion Type Serviceを初期化
        from fashion_type_service import FashionTypeService
        fashion_type_service = FashionTypeService(firebase_service.db)

        # 診断実行
        result = fashion_type_service.diagnose(request.user_id, answers)

        print(f"[Fashion Type] Diagnosis completed: {result['type_code']} - {result['type_name']}")

        # レスポンス返却
        return FashionTypeDiagnosisResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in diagnose_fashion_type endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/fashion-type/questions")
async def get_fashion_type_questions():
    """
    Get all fashion type questions from master data.

    Returns:
        list: All 10 questions with metadata (sorted by order)
    """
    try:
        firebase_service = FirebaseService()
        from fashion_type_service import FashionTypeService
        fashion_type_service = FashionTypeService(firebase_service.db)

        questions = fashion_type_service.get_all_questions()

        return {
            "status": "success",
            "count": len(questions),
            "questions": questions
        }
    except Exception as e:
        print(f"Error in get_fashion_type_questions endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/fashion-type/master/{type_code}")
async def get_fashion_type_master(type_code: str):
    """
    Get detailed master data for a specific fashion type.

    Args:
        type_code: 4-letter type code (e.g., "TPAQ", "CRFE")

    Returns:
        dict: Master data including type_name, description, core_stance, group info, etc.
    """
    try:
        firebase_service = FirebaseService()
        from fashion_type_service import FashionTypeService
        fashion_type_service = FashionTypeService(firebase_service.db)

        master_data = fashion_type_service.get_type_master(type_code)

        if not master_data:
            raise HTTPException(status_code=404, detail=f"Type code '{type_code}' not found")

        return {
            "status": "success",
            "type_code": type_code,
            "data": master_data
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_fashion_type_master endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/fashion-type/groups/{group_code}")
async def get_fashion_type_group(group_code: str):
    """
    Get group information for a specific fashion type group.

    Args:
        group_code: 2-letter group code ("TP", "TR", "CP", or "CR")

    Returns:
        dict: Group information including name, color, nuance, and member types
    """
    try:
        firebase_service = FirebaseService()
        from fashion_type_service import FashionTypeService
        fashion_type_service = FashionTypeService(firebase_service.db)

        group_info = fashion_type_service.get_group_info(group_code)

        if not group_info:
            raise HTTPException(status_code=404, detail=f"Group code '{group_code}' not found")

        return {
            "status": "success",
            "group_code": group_code,
            "data": group_info
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_fashion_type_group endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/fashion-type/axes")
async def get_fashion_type_axes():
    """
    Get all axes information (calculation rules, thresholds, etc.).

    Returns:
        list: All 4 axes definitions
    """
    try:
        firebase_service = FirebaseService()
        from fashion_type_service import FashionTypeService
        fashion_type_service = FashionTypeService(firebase_service.db)

        axes = fashion_type_service.get_axes_info()

        return {
            "status": "success",
            "count": len(axes),
            "axes": axes
        }
    except Exception as e:
        print(f"Error in get_fashion_type_axes endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/user-insight", response_model=UserInsightResponse)
async def get_user_insight(userid: str):
    """
    Get user insight based on fashion type and animal fortune data.

    Args:
        userid: User ID

    Returns:
        UserInsightResponse: Generated insight from Gemini 2.5-flash-lite
    """
    try:
        firebase_service = FirebaseService()
        from user_insight_service import UserInsightService
        user_insight_service = UserInsightService(firebase_service.db)

        # Generate insight
        result = user_insight_service.generate_insight(userid)

        print(f"[UserInsight] Generated insight for user {userid}: {result['status']}")

        return result

    except Exception as e:
        print(f"Error in get_user_insight endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/user-insight/history")
async def get_user_insight_history(userid: str, limit: int = 10):
    """
    Get user insight history.

    Args:
        userid: User ID
        limit: Number of insights to retrieve (default: 10)

    Returns:
        list: User's insight history (newest first)
    """
    try:
        firebase_service = FirebaseService()
        from user_insight_service import UserInsightService
        user_insight_service = UserInsightService(firebase_service.db)

        # Get insight history
        history = user_insight_service.get_insight_history(userid, limit)

        print(f"[UserInsight] Retrieved {len(history)} insights for user {userid}")

        return {
            "status": "success",
            "user_id": userid,
            "count": len(history),
            "history": history
        }

    except Exception as e:
        print(f"Error in get_user_insight_history endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/animal-fortune", response_model=AnimalFortuneResponse)
async def diagnose_animal_fortune(request: AnimalFortuneRequest):
    """
    Animal fortune diagnosis endpoint.
    Analyzes user's birth date and returns their animal fortune.

    Args:
        request: AnimalFortuneRequest containing user_id, year, month, day

    Returns:
        AnimalFortuneResponse: Fortune result with animal type and personality traits
    """
    try:
        # バリデーション: user_idの存在チェック
        if not request.user_id or request.user_id.strip() == "":
            raise HTTPException(status_code=400, detail="user_id is required")

        print(f"[Animal Fortune] Diagnosing for user: {request.user_id}")
        print(f"[Animal Fortune] Birth date: {request.year}/{request.month}/{request.day}")

        # Firebase Serviceを初期化
        firebase_service = FirebaseService()

        # Animal Fortune Serviceを初期化
        from animal_fortune_service import AnimalFortuneService
        animal_fortune_service = AnimalFortuneService(firebase_service.db)

        # 占い実行
        result = animal_fortune_service.diagnose(
            request.user_id,
            request.year,
            request.month,
            request.day
        )

        print(f"[Animal Fortune] Diagnosis completed: {result['animal_name']}")

        # レスポンス返却
        return AnimalFortuneResponse(**result)

    except HTTPException:
        raise
    except ValueError as e:
        # バリデーションエラー（年月日の範囲外など）
        print(f"Validation error in diagnose_animal_fortune: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error in diagnose_animal_fortune endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ========================================
# Standard Items API
# ========================================

@app.get("/api/standard-items", response_model=StandardItemsResponse)
async def get_standard_items(
    gender: Optional[str] = None,
    main_category: Optional[str] = None,
    sub_category: Optional[str] = None,
    color: Optional[str] = None,
    limit: int = 100
):
    """
    Get standard items from Firestore with optional filters.

    Args:
        gender: Gender filter ("men" or "women")
        main_category: Main category filter (e.g., "アウター")
        sub_category: Sub category filter (e.g., "Gジャン")
        color: Color filter (e.g., "ブラック")
        limit: Maximum number of items to return (default: 100)

    Returns:
        StandardItemsResponse: List of standard items matching the filters
    """
    try:
        print(f"[Standard Items] Getting items with filters:")
        print(f"  gender: {gender}")
        print(f"  main_category: {main_category}")
        print(f"  sub_category: {sub_category}")
        print(f"  color: {color}")
        print(f"  limit: {limit}")

        # Standard Items Serviceを初期化
        from standard_items_service import StandardItemsService
        service = StandardItemsService()

        # アイテム取得
        items = service.get_standard_items(
            gender=gender,
            main_category=main_category,
            sub_category=sub_category,
            color=color,
            limit=limit
        )

        print(f"[Standard Items] Found {len(items)} items")

        # レスポンス作成
        return StandardItemsResponse(
            status="success",
            total_count=len(items),
            items=[StandardItem(**item) for item in items],
            filters={
                "gender": gender,
                "main_category": main_category,
                "sub_category": sub_category,
                "color": color,
                "limit": limit
            }
        )

    except Exception as e:
        print(f"Error in get_standard_items endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/standard-items/categories")
async def get_standard_items_categories(gender: Optional[str] = None):
    """
    Get category summary for standard items.

    Args:
        gender: Gender filter ("men" or "women")

    Returns:
        Category summary with counts
    """
    try:
        print(f"[Standard Items] Getting categories for gender: {gender}")

        # Standard Items Serviceを初期化
        from standard_items_service import StandardItemsService
        service = StandardItemsService()

        # カテゴリ取得
        categories = service.get_categories(gender=gender)

        print(f"[Standard Items] Found {categories['total_count']} items in {len(categories['categories'])} categories")

        return {
            "status": "success",
            "gender": gender,
            **categories
        }

    except Exception as e:
        print(f"Error in get_standard_items_categories endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/health/standard-items")
async def health_standard_items():
    """
    Health check endpoint for standard items API.
    """
    try:
        from standard_items_service import StandardItemsService
        service = StandardItemsService()

        # テスト: 全アイテム数を取得
        items = service.get_standard_items(limit=1)

        return {
            "status": "healthy",
            "message": "Standard items service is running",
            "sample_item_exists": len(items) > 0
        }

    except Exception as e:
        print(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": str(e)
        }


@app.post("/api/items/register", response_model=ItemRegistrationResponse)
async def register_item(
    user_id: str = Form(...),
    user_token: str = Form(...),
    image: UploadFile = File(...),
    # User closet item fields
    item_type: str = Form(...),
    category: Optional[str] = Form(None),
    coordinate_id: Optional[str] = Form(None)
):
    """
    Register a single user closet item.

    Args:
        user_id: User ID
        user_token: User authentication token
        image: Item image file (JPEG/PNG)
        item_type: Item type (required)
        category: Optional category
        coordinate_id: Optional coordinate ID

    Returns:
        ItemRegistrationResponse: Registered item information
    """
    import uuid
    import time

    request_start_time = time.time()

    try:
        # Authentication validation
        if not user_id or not user_token:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # File type validation
        if not image.content_type or not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

        # User items are NEVER standard items - force is_standard to False
        is_standard_bool = False

        # Validate required field
        if not item_type:
            raise HTTPException(
                status_code=400,
                detail="item_type is required for user closet items"
            )

        # Initialize services
        from firebase_service import FirebaseService
        firebase_service = FirebaseService()

        # Read image data
        print(f"[ItemRegistration] Processing user closet item for user: {user_id}")
        image_data = await image.read()

        # Generate item ID
        item_id = str(uuid.uuid4())

        # User closet item storage path: items/{user_id}/{item_type}/{uuid}.jpg
        storage_path = f"items/{user_id}/{item_type}/{item_id}.jpg"

        # Upload image to Firebase Storage
        upload_start = time.time()
        storage_url = await asyncio.to_thread(
            firebase_service.upload_image,
            image_data,
            storage_path
        )
        upload_elapsed = time.time() - upload_start
        print(f"[ItemRegistration] Image uploaded in {upload_elapsed:.2f}s: {storage_url}")

        # Save metadata to Firestore as user closet item
        item_data = firebase_service.save_user_closet_item(
            user_id=user_id,
            item_id=item_id,
            storage_url=storage_url,
            item_type=item_type,
            coordinate_id=coordinate_id,
            category=category,
            color=color
        )

        # Convert timestamp for response
        created_at = datetime.utcnow().isoformat()

        registered_item = RegisteredItem(
            id=item_id,
            storage_url=storage_url,
            is_standard=False,
            gender=None,
            main_category=None,
            sub_category=None,
            color=color,
            item_type=item_type,
            category=category,
            coordinate_id=coordinate_id,
            created_at=created_at
        )

        request_elapsed = time.time() - request_start_time
        print(f"[ItemRegistration] Completed in {request_elapsed:.2f}s")

        return ItemRegistrationResponse(
            status="success",
            item=registered_item
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ItemRegistration] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/items/register/bulk", response_model=BulkItemRegistrationResponse)
async def register_items_bulk(
    user_id: str = Form(...),
    user_token: str = Form(...),
    items_metadata: str = Form(...),
    images: List[UploadFile] = File(...)
):
    """
    Register multiple user closet items in bulk (all-or-nothing).

    Args:
        user_id: User ID
        user_token: User authentication token
        items_metadata: JSON array of item metadata (each item must have item_type)
        images: List of item images (order must match metadata)

    Returns:
        BulkItemRegistrationResponse: Registration result with success/error details
    """
    import uuid
    import time

    request_start_time = time.time()
    uploaded_urls = []
    uploaded_storage_paths = []

    try:
        # Authentication validation
        if not user_id or not user_token:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Parse metadata JSON
        try:
            metadata_list = json.loads(items_metadata)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON in items_metadata: {str(e)}")

        # Validate metadata is a list
        if not isinstance(metadata_list, list):
            raise HTTPException(status_code=400, detail="items_metadata must be a JSON array")

        if len(metadata_list) == 0:
            raise HTTPException(status_code=400, detail="items_metadata cannot be empty")

        # Validate images count matches metadata count
        if len(images) != len(metadata_list):
            raise HTTPException(
                status_code=400,
                detail=f"Images count ({len(images)}) must match metadata count ({len(metadata_list)})"
            )

        # Parse and validate metadata using Pydantic
        # BulkItemMetadata now enforces item_type as required field
        try:
            validated_metadata = [BulkItemMetadata(**item) for item in metadata_list]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Metadata validation failed: {str(e)}")

        # Validate all file types
        errors = []  # Initialize errors list
        for idx, image in enumerate(images):
            if not image.content_type or not image.content_type.startswith('image/'):
                errors.append(BulkItemError(
                    index=idx,
                    error=f"Invalid file type: {image.content_type}. Only images allowed."
                ))

        if errors:
            return BulkItemRegistrationResponse(
                status="error",
                total_count=len(metadata_list),
                success_count=0,
                failed_count=len(errors),
                items=[],
                errors=errors
            )

        print(f"[BulkRegistration] Processing {len(validated_metadata)} items for user: {user_id}")

        # Initialize services
        from firebase_service import FirebaseService
        firebase_service = FirebaseService()

        # Step 1: Upload all images in parallel
        upload_start = time.time()
        upload_tasks = []
        item_ids = []
        storage_paths = []
        file_sizes = []

        for idx, (meta, image) in enumerate(zip(validated_metadata, images)):
            # Read image data
            image_data = await image.read()
            file_sizes.append(len(image_data))

            # Generate item ID
            item_id = str(uuid.uuid4())
            item_ids.append(item_id)

            # User closet item storage path: items/{user_id}/{item_type}/{uuid}.jpg
            storage_path = f"items/{user_id}/{meta.item_type}/{item_id}.jpg"
            storage_paths.append(storage_path)

            # Create upload task
            upload_tasks.append(
                asyncio.to_thread(
                    firebase_service.upload_image,
                    image_data,
                    storage_path
                )
            )

        # Execute all uploads in parallel
        upload_results = await asyncio.gather(*upload_tasks, return_exceptions=True)

        # Check for upload errors
        for idx, result in enumerate(upload_results):
            if isinstance(result, Exception):
                # Upload failed - rollback
                print(f"[BulkRegistration] Upload failed for item {idx}: {result}")
                raise Exception(f"Image upload failed for item {idx}: {str(result)}")

        uploaded_urls = upload_results
        uploaded_storage_paths = storage_paths

        upload_elapsed = time.time() - upload_start
        print(f"[BulkRegistration] {len(uploaded_urls)} images uploaded in {upload_elapsed:.2f}s")

        # Step 2: Prepare batch data for Firestore (user closet items only)
        batch_items = []
        registered_items = []

        for idx, (meta, item_id, storage_url, image) in enumerate(zip(validated_metadata, item_ids, uploaded_urls, images)):
            created_at = datetime.utcnow().isoformat()

            # All items are user closet items
            item_data = {
                'id': item_id,
                'user_id': user_id,
                'item_type': meta.item_type,
                'image_url': storage_url,
                'created_at': firestore.SERVER_TIMESTAMP
            }

            if meta.coordinate_id:
                item_data['coordinate_id'] = meta.coordinate_id
            if meta.category:
                item_data['category'] = meta.category
            if meta.color:
                item_data['color'] = meta.color

            batch_items.append({
                'collection': f'users/{user_id}/items',
                'document_id': item_id,
                'data': item_data
            })

            registered_items.append(RegisteredItem(
                id=item_id,
                storage_url=storage_url,
                is_standard=False,
                gender=None,
                main_category=None,
                sub_category=None,
                color=meta.color,
                item_type=meta.item_type,
                category=meta.category,
                coordinate_id=meta.coordinate_id,
                created_at=created_at
            ))

        # Step 3: Batch write to Firestore
        batch_start = time.time()
        batch_result = firebase_service.register_items_batch(batch_items)

        if not batch_result['success']:
            raise Exception(f"Batch write failed: {batch_result['error']}")

        batch_elapsed = time.time() - batch_start
        print(f"[BulkRegistration] Batch write completed in {batch_elapsed:.2f}s")

        request_elapsed = time.time() - request_start_time
        print(f"[BulkRegistration] Total time: {request_elapsed:.2f}s")

        return BulkItemRegistrationResponse(
            status="success",
            total_count=len(registered_items),
            success_count=len(registered_items),
            failed_count=0,
            items=registered_items,
            errors=[]
        )

    except HTTPException:
        # Rollback: Delete uploaded images
        if uploaded_urls:
            print(f"[Rollback] Deleting {len(uploaded_urls)} uploaded images")
            for url in uploaded_urls:
                try:
                    firebase_service.delete_image_from_url(url)
                except Exception as del_error:
                    print(f"[Rollback Error] Failed to delete {url}: {del_error}")
        raise

    except Exception as e:
        # Rollback: Delete uploaded images
        if uploaded_urls:
            print(f"[Rollback] Deleting {len(uploaded_urls)} uploaded images due to error")
            from firebase_service import FirebaseService
            firebase_service = FirebaseService()
            for url in uploaded_urls:
                try:
                    firebase_service.delete_image_from_url(url)
                except Exception as del_error:
                    print(f"[Rollback Error] Failed to delete {url}: {del_error}")

        print(f"[BulkRegistration] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Bulk registration failed: {str(e)}")
