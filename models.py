from pydantic import BaseModel, validator
from typing import List, Optional
from enum import Enum


class Gender(str, Enum):
    men = "men"
    women = "women"
    other = "other"


class RecommendCoordinatesRequest(BaseModel):
    gender: Gender


class AffiliateProduct(BaseModel):
    name: str
    price: int
    url: str
    image_url: str
    store_name: str


class CoordinateItem(BaseModel):
    id: int
    image_url: str
    pin_url_guess: str
    coordinate_review: Optional[str] = None
    tops_categorize: Optional[str] = None
    bottoms_categorize: Optional[str] = None
    affiliate_tops: List[AffiliateProduct] = []
    affiliate_bottoms: List[AffiliateProduct] = []


class GenreCount(BaseModel):
    genre: str
    count: int


class AnalysisCoordinateResponse(BaseModel):
    id: int
    coordinate_review: Optional[str] = None
    tops_categorize: Optional[str] = None
    bottoms_categorize: Optional[str] = None
    affiliate_tops: List[AffiliateProduct] = []
    affiliate_bottoms: List[AffiliateProduct] = []


class RecommendCoordinatesResponse(BaseModel):
    coordinates: List[CoordinateItem]
    genres: List[GenreCount]
    recommend_reasons: Optional[str] = None


class ChatRequest(BaseModel):
    question: str
    gender: Gender
    image_base64: Optional[str] = None
    model: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str


# Fashion Review Models
class FashionReviewCurrentCoordinate(BaseModel):
    id: str
    date: str
    coodinate_image_path: str  # Note: typo in iOS model, keeping for compatibility


class FashionReviewRecentCoordinate(BaseModel):
    id: str
    date: str
    coodinate_image_path: str  # Note: typo in iOS model, keeping for compatibility
    ai_catchphrase: str
    ai_review_comment: str


class FashionReviewItem(BaseModel):
    id: str
    coordinate_id: str
    item_type: str
    item_image_path: str
    category: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None


class FashionReviewResponse(BaseModel):
    current_coordinate: FashionReviewCurrentCoordinate
    recent_coordinates: List[FashionReviewRecentCoordinate]
    items: List[FashionReviewItem]
    ai_catchphrase: str
    ai_review_comment: str
    tags: Optional[List[str]] = None
    item_types: Optional[List[str]] = None  # List of found item types (e.g., ["アウター", "トップス", "ボトムス"])


# Coordinate Recommend Models
class CoordinateRecommendRequest(BaseModel):
    gender: Gender
    input_type: str
    category: str
    text: str
    num_outfits: int = 3
    num_candidates: int = 5


# Home API Models
class HomeRecentCoordinate(BaseModel):
    id: str
    image_url: str
    date: str

class HomeResponse(BaseModel):

    recent_coordinates: List[HomeRecentCoordinate]

    analysis_summary: str

    tags: List[str]





# Closet API Models

class ClosetItem(BaseModel):

    id: str

    item_type: str

    category: Optional[str] = None

    color: Optional[str] = None

    image_url: Optional[str] = None

    date: Optional[str] = None



class ClosetResponse(BaseModel):

    items: List[ClosetItem]


# Analyze Recent Coordinate API Models
class AnalyzeRecentCoordinateRequest(BaseModel):
    uid: str
    target_days: int = 7

class AnalyzeRecentCoordinateResponse(BaseModel):
    analyze_recent_coordinate: str


# Calendar API Models
class CoordinateListItem(BaseModel):
    year: int
    month: int
    day: int
    id: Optional[str] = None
    coodinate_image_path: Optional[str] = None  # Note: typo matches iOS client


class CoordinateDetailCurrentCoordinate(BaseModel):
    id: str
    date: str  # YYYY-MM-DD
    coodinate_image_path: str  # Note: typo matches iOS client


class CoordinateDetailItem(BaseModel):
    id: str
    coordinate_id: str
    item_type: str
    item_image_path: str


class CoordinateDetailResponse(BaseModel):
    current_coordinate: CoordinateDetailCurrentCoordinate
    items: List[CoordinateDetailItem]
    ai_catchphrase: str
    ai_review_comment: str


# Gemini Test Models
class GeminiTestRequest(BaseModel):
    model: str
    prompt: str


class GeminiTestResponse(BaseModel):
    response: str


# Delete Coordinate Models
class DeleteCoordinateRequest(BaseModel):
    uid: str
    coordinate_id: str


class DeleteCoordinateResponse(BaseModel):
    success: bool
    message: str
    deleted_items_count: int


# Fashion Type Diagnosis Models
class FashionTypeDiagnosisRequest(BaseModel):
    user_id: str
    Q1: int  # 1-5
    Q2: int  # 1-5
    Q3: int  # 1-5
    Q4: int  # 1-5
    Q5: int  # 1-5
    Q6: int  # 1-5
    Q7: int  # 1-5
    Q8: int  # 1-5
    Q9: int  # 1-5
    Q10: int  # 1-5

    @validator('Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Q7', 'Q8', 'Q9', 'Q10')
    def validate_score(cls, v):
        if not 1 <= v <= 5:
            raise ValueError('Score must be between 1 and 5')
        return v


class FashionTypeDiagnosisResponse(BaseModel):
    diagnosis_id: str
    type_code: str  # 4文字コード (e.g., "TPAQ")
    type_name: str  # タイプ名 (e.g., "アヴァンギャルド・スター")
    trend_score: float  # 流行スコア (1.0-5.0)
    self_score: float  # 自己スコア (1.0-5.0)
    social_score: float  # 社会スコア (1.0-5.0)
    function_score: float  # 機能スコア (1.0-5.0)
    economy_score: float  # 経済スコア (1.0-5.0)
    created_at: str  # ISO format datetime
