from pydantic import BaseModel
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