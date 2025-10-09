import csv
import random
import asyncio
from typing import List, Dict
from collections import defaultdict
from models import CoordinateItem, Gender, AffiliateProduct
from yahoo_shopping import YahooShoppingClient
from gemini_service import GeminiService


class CoordinateService:
    @staticmethod
    def get_coordinates_by_gender(gender: Gender) -> List[CoordinateItem]:
        coordinates = []
        
        if gender == Gender.other:
            # otherの場合はmenとwomenの両方を取得
            coordinates.extend(CoordinateService._read_csv_file("data/analysis-coordinate/men/coordinates.csv"))
            coordinates.extend(CoordinateService._read_csv_file("data/analysis-coordinate/women/coordinates.csv"))
        else:
            # men または women の場合
            file_path = f"data/analysis-coordinate/{gender.value}/coordinates.csv"
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
                        pin_url_guess=row['pin_url_guess'],
                        coordinate_review=row.get('coordinate_review', ''),
                        tops_categorize=row.get('tops_categorize', ''),
                        bottoms_categorize=row.get('bottoms_categorize', '')
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
        
        # 全てのコーディネートからランダムに3件選択
        all_coordinates = []
        for coords in genre_groups.values():
            all_coordinates.extend(coords)
        
        # 利用可能なコーディネートをシャッフル
        random.shuffle(all_coordinates)
        selected_coordinates = all_coordinates[:3]
        
        final_coordinates = selected_coordinates
        
        # 最終的に選択された3個のコーディネートのジャンル別件数を取得
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
            file_paths = ["data/analysis-coordinate/men/coordinates.csv", "data/analysis-coordinate/women/coordinates.csv"]
        else:
            file_paths = [f"data/analysis-coordinate/{gender.value}/coordinates.csv"]
        
        # 3. genreでグループ化してランダム選択
        result = CoordinateService.group_by_genre_and_select_random(coordinates, file_paths)
        
        # 4. Yahoo商品検索を追加
        yahoo_client = YahooShoppingClient()
        gender_jp = "メンズ" if gender.value == "men" else "レディース" if gender.value == "women" else "メンズ"
        
        for coord in result['coordinates']:
            # トップス商品検索
            if coord.tops_categorize:
                tops_query = yahoo_client.extract_search_keywords(coord.tops_categorize)
                tops_products = yahoo_client.search_products(tops_query, gender_jp, 15)
                coord.affiliate_tops = [AffiliateProduct(**product) for product in tops_products]
            
            # ボトムス商品検索
            if coord.bottoms_categorize:
                bottoms_query = yahoo_client.extract_search_keywords(coord.bottoms_categorize)
                bottoms_products = yahoo_client.search_products(bottoms_query, gender_jp, 15)
                coord.affiliate_bottoms = [AffiliateProduct(**product) for product in bottoms_products]

        # Gemini APIを使ってrecommend_reasonsを生成
        gemini_service = GeminiService()
        recommend_reasons = gemini_service.generate_recommend_reasons(result['coordinates'])
        result['recommend_reasons'] = recommend_reasons

        return result
    
    @staticmethod
    async def recommend_coordinates_async(gender: Gender) -> Dict:
        # 1. genderに基づいてCSVファイルを読み込み
        coordinates = CoordinateService.get_coordinates_by_gender(gender)
        
        # 2. ファイルパスを決定
        file_paths = []
        if gender == Gender.other:
            file_paths = ["data/analysis-coordinate/men/coordinates.csv", "data/analysis-coordinate/women/coordinates.csv"]
        else:
            file_paths = [f"data/analysis-coordinate/{gender.value}/coordinates.csv"]
        
        # 3. genreでグループ化してランダム選択
        result = CoordinateService.group_by_genre_and_select_random(coordinates, file_paths)
        
        # 4. Yahoo商品検索を並行処理で追加
        yahoo_client = YahooShoppingClient()
        gender_jp = "メンズ" if gender.value == "men" else "レディース" if gender.value == "women" else "メンズ"
        
        # 並行処理用のタスクを作成
        tasks = []
        task_info = []  # タスクがどのコーディネートのどのカテゴリに対応しているかを追跡
        
        for coord in result['coordinates']:
            # トップス商品検索
            if coord.tops_categorize:
                tops_query = yahoo_client.extract_search_keywords(coord.tops_categorize)
                task = yahoo_client.search_products_async(tops_query, gender_jp, 15)
                tasks.append(task)
                task_info.append((coord, 'tops'))
            
            # ボトムス商品検索
            if coord.bottoms_categorize:
                bottoms_query = yahoo_client.extract_search_keywords(coord.bottoms_categorize)
                task = yahoo_client.search_products_async(bottoms_query, gender_jp, 15)
                tasks.append(task)
                task_info.append((coord, 'bottoms'))
        
        # すべてのAPIコールを並行実行
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 結果を各コーディネートに割り当て
            for i, (coord, category) in enumerate(task_info):
                if not isinstance(results[i], Exception) and results[i]:
                    if category == 'tops':
                        coord.affiliate_tops = [AffiliateProduct(**product) for product in results[i]]
                    else:
                        coord.affiliate_bottoms = [AffiliateProduct(**product) for product in results[i]]

        # Gemini APIを使ってrecommend_reasonsを生成
        gemini_service = GeminiService()
        recommend_reasons = await gemini_service.generate_recommend_reasons_async(result['coordinates'])
        result['recommend_reasons'] = recommend_reasons

        return result