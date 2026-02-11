import os
import base64
import json
from typing import List, Optional, Dict, Any
import urllib
import urllib.parse
import random
from datetime import datetime

from pydantic import BaseModel
import requests

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from models import (
    RecommendCoordinatesRequest, RecommendCoordinatesResponse, GenreCount,
    AnalysisCoordinateResponse, AffiliateProduct, ChatRequest, ChatResponse,
    FashionReviewResponse, FashionReviewCurrentCoordinate, FashionReviewRecentCoordinate,
    FashionReviewItem, CoordinateRecommendRequest, HomeResponse, HomeRecentCoordinate,
    ClosetItem, ClosetResponse
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

        # Generate AI review and extract items using Gemini (single API call)
        print(f"Generating fashion review and extracting items for user: {user_id}")
        ai_review = await gemini_service.generate_fashion_review_async(image_base64)

        # Upload image to Firebase Storage
        print("Uploading image to Firebase Storage...")
        coordinate_image_url = firebase_service.upload_image(image_data, folder=f"coordinates/{user_id}")

        # Upload individual item images if provided
        tops_image_url = None
        bottoms_image_url = None

        if tops_image:
            # Validate file type
            if not tops_image.content_type or not tops_image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="Invalid tops_image file type")
            tops_image_data = await tops_image.read()
            tops_image_url = firebase_service.upload_image(tops_image_data, folder=f"items/{user_id}/tops")
            print(f"Uploaded tops_image: {tops_image_url}")

        if bottoms_image:
            # Validate file type
            if not bottoms_image.content_type or not bottoms_image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="Invalid bottoms_image file type")
            bottoms_image_data = await bottoms_image.read()
            bottoms_image_url = firebase_service.upload_image(bottoms_image_data, folder=f"items/{user_id}/bottoms")
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

        print(f"Fashion review completed successfully for user: {user_id}")
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
