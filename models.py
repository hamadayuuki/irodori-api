from pydantic import BaseModel
from typing import List
from enum import Enum


class Gender(str, Enum):
    men = "men"
    women = "women"
    other = "other"


class RecommendCoordinatesRequest(BaseModel):
    gender: Gender


class CoordinateItem(BaseModel):
    id: int
    image_url: str
    pin_url_guess: str


class RecommendCoordinatesResponse(BaseModel):
    coordinates: List[CoordinateItem]