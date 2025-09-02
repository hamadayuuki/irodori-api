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
    def group_by_genre_and_select_random(coordinates: List[CoordinateItem], file_paths: List[str]) -> Dict:
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
        
        # 全てのコーディネートからランダムに10件選択
        all_coordinates = []
        for coords in genre_groups.values():
            all_coordinates.extend(coords)
        
        # 利用可能なコーディネートをシャッフル
        random.shuffle(all_coordinates)
        selected_coordinates = all_coordinates[:10]
        
        final_coordinates = selected_coordinates
        
        # 最終的に選択された10個のコーディネートのジャンル別件数を取得
        genre_counts = {}
        for coord in final_coordinates:
            for genre, coords in genre_groups.items():
                if coord in coords:
                    genre_counts[genre] = genre_counts.get(genre, 0) + 1
                    break
        
        return {
            'coordinates': final_coordinates,
            'genres': genre_counts
        }
    
    @staticmethod
    def recommend_coordinates(gender: Gender) -> Dict:
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