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


class ChatResponse(BaseModel):
    answer: str