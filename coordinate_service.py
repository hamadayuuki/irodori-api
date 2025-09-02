import csv
import random
from typing import List, Dict
from collections import defaultdict
from models import CoordinateItem, Gender


class CoordinateService:
    @staticmethod
    def get_coordinates_by_gender(gender: Gender) -> List[CoordinateItem]:
        coordinates = []
        
        if gender == Gender.other:
            # otherの場合はmenとwomenの両方を取得
            coordinates.extend(CoordinateService._read_csv_file("data/men/coordinates.csv"))
            coordinates.extend(CoordinateService._read_csv_file("data/women/coordinates.csv"))
        else:
            # men または women の場合
            file_path = f"data/{gender.value}/coordinates.csv"
            coordinates = CoordinateService._read_csv_file(file_path)
        
        return coordinates
    
    @staticmethod
    def _read_csv_file(file_path: str) -> List[CoordinateItem]:
        coordinates = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    coordinate = CoordinateItem(
                        id=int(row['id']),
                        image_url=row['image_url'],
                        pin_url_guess=row['pin_url_guess']
                    )
                    coordinates.append(coordinate)
        except FileNotFoundError:
            print(f"File not found: {file_path}")
        except Exception as e:
            print(f"Error reading CSV file {file_path}: {e}")
        
        return coordinates
    
    @staticmethod
    def group_by_genre_and_select_random(coordinates: List[CoordinateItem], file_paths: List[str]) -> List[CoordinateItem]:
        # genreでグループ化するため、CSVを再読み込みしてgenre情報を取得
        genre_groups = defaultdict(list)
        
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        genre = row['genre']
                        coordinate_id = int(row['id'])
                        
                        # coordinatesリストから対応するCoordinateItemを見つける
                        for coord in coordinates:
                            if coord.id == coordinate_id:
                                genre_groups[genre].append(coord)
                                break
            except Exception as e:
                print(f"Error reading CSV file {file_path} for genre grouping: {e}")
        
        # 各genreからランダムで選択し、最大10個まで
        selected_coordinates = []
        
        for genre, coords in genre_groups.items():
            if coords:
                # 各genreから1つずつランダム選択
                selected = random.choice(coords)
                selected_coordinates.append(selected)
        
        # 結果をシャッフルして最大10個まで
        random.shuffle(selected_coordinates)
        return selected_coordinates[:10]
    
    @staticmethod
    def recommend_coordinates(gender: Gender) -> List[CoordinateItem]:
        # 1. genderに基づいてCSVファイルを読み込み
        coordinates = CoordinateService.get_coordinates_by_gender(gender)
        
        # 2. ファイルパスを決定
        file_paths = []
        if gender == Gender.other:
            file_paths = ["data/men/coordinates.csv", "data/women/coordinates.csv"]
        else:
            file_paths = [f"data/{gender.value}/coordinates.csv"]
        
        # 3. genreでグループ化してランダム選択
        return CoordinateService.group_by_genre_and_select_random(coordinates, file_paths)