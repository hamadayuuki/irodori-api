import os
import csv
import json
import base64
import requests
from typing import List, Dict, Optional
import shutil
from pathlib import Path

from openai import OpenAI

class CoordinateAnalyzer:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.gpt_model = "gpt-4o-mini"
        
    def read_coordinates_csv(self, file_path: str) -> List[Dict]:
        """coordinates.csvからidとimage_urlを取得"""
        coordinates = []
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    coordinates.append({
                        'id': int(row['id']),
                        'image_url': row['image_url'],
                        'original_data': row  # 元のデータも保持
                    })
        except FileNotFoundError:
            print(f"File not found: {file_path}")
        except Exception as e:
            print(f"Error reading CSV file {file_path}: {e}")
        
        return coordinates
    
    def download_image(self, image_url: str) -> Optional[str]:
        """image_urlから全身画像を取得してbase64エンコード"""
        try:
            response = requests.get(image_url)
            response.raise_for_status()
            image_data = response.content
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            return encoded_image
        except Exception as e:
            print(f"Error downloading image from {image_url}: {e}")
            return None
    
    def analyze_coordinate_with_gpt(self, image_base64: str, gender: str) -> Optional[Dict]:
        """ChatGPTに画像を送信してanalysisCoordinate相当のレスポンスを取得"""
        system_prompt = """
        あなたはプロのファッションコーディネーターです。服飾の知識が豊富です。
        必ずJSON形式で回答してください。jsonのvalueには可能な限り日本語を使ってください。
        """

        prompt = """
        添付する全身画像を解析し、以下のJSON形式で回答してください。

        ## 出力形式（必ずJSON形式）
        {
            "coordinate_review": "コーディネート全体の印象やレビューを150〜200文字程度で記述。回答するときはコーディネートを対象にすることが重要です背景等は判断に含めないようにしてください。",
            "tops_categorize": "トップスのカテゴリを <アイテム名> <柄(分かるなら記載する)> <サイズ(分かるなら記載する)> <カラー>（例：パンツ ストライプ ワイド ブラック）",
            "bottoms_categorize": "ボトムスのカテゴリ <アイテム名> <柄(分かるなら記載する)> <サイズ(分かるなら記載する)> <カラー>（例：Tシャツ タイト ホワイト）"
        }

        ## 注意事項
        - 必ずJSON形式で回答してください
        - 他の形式での回答は禁止です
        - JSONの値は全て文字列型です
        """

        try:
            response = self.client.chat.completions.create(
                model=self.gpt_model,
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
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_completion_tokens=4096,
                response_format={"type": "json_object"}
            )
            
            # JSONレスポンスをパース
            response_data = json.loads(response.choices[0].message.content)
            return response_data
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return None
        except Exception as e:
            print(f"Error calling GPT API: {e}")
            return None
    
    def copy_csv_files(self):
        """coordinates.csvをchatgpt/women、chatgpt/menにコピー"""
        # ディレクトリを作成
        Path("/Users/hamadayuuki/Desktop/render/irodori-api/data/chatgpt/women").mkdir(parents=True, exist_ok=True)
        Path("/Users/hamadayuuki/Desktop/render/irodori-api/data/chatgpt/men").mkdir(parents=True, exist_ok=True)
        
        # women/coordinates.csvをコピー
        shutil.copy2(
            "/Users/hamadayuuki/Desktop/render/irodori-api/data/women/coordinates.csv",
            "/Users/hamadayuuki/Desktop/render/irodori-api/data/chatgpt/women/coordinates.csv"
        )
        
        # men/coordinates.csvをコピー
        shutil.copy2(
            "/Users/hamadayuuki/Desktop/render/irodori-api/data/men/coordinates.csv",
            "/Users/hamadayuuki/Desktop/render/irodori-api/data/chatgpt/men/coordinates.csv"
        )
        
        print("CSV files copied successfully")
    
    def update_csv_with_analysis(self, csv_path: str, coordinate_data: List[Dict]):
        """coordinate_review, tops_categorize, bottoms_categorizeをCSVの末尾に追加"""
        # 既存のCSVを読み込み
        existing_data = []
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames
            existing_data = list(reader)
        
        # 新しいフィールドを追加
        new_fieldnames = list(fieldnames) + ['coordinate_review', 'tops_categorize', 'bottoms_categorize']
        
        # データを更新
        for row in existing_data:
            row_id = int(row['id'])
            # 対応する解析データを見つける
            for coord in coordinate_data:
                if coord['id'] == row_id and 'analysis' in coord:
                    analysis = coord['analysis']
                    row['coordinate_review'] = analysis.get('coordinate_review', '')
                    row['tops_categorize'] = analysis.get('tops_categorize', '')
                    row['bottoms_categorize'] = analysis.get('bottoms_categorize', '')
                    break
            else:
                # 解析データがない場合は空文字
                row['coordinate_review'] = ''
                row['tops_categorize'] = ''
                row['bottoms_categorize'] = ''
        
        # CSVに書き戻し
        with open(csv_path, 'w', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=new_fieldnames)
            writer.writeheader()
            writer.writerows(existing_data)
        
        print(f"Updated CSV file: {csv_path}")
    
    def process_gender(self, gender: str, limit: Optional[int] = None):
        """特定の性別のデータを処理"""
        print(f"Processing {gender} coordinates...")
        
        # CSVファイルパス
        source_csv = f"/Users/hamadayuuki/Desktop/render/irodori-api/data/{gender}/coordinates.csv"
        target_csv = f"/Users/hamadayuuki/Desktop/render/irodori-api/data/chatgpt/{gender}/coordinates.csv"
        
        # coordinates.csvを読み込み
        coordinates = self.read_coordinates_csv(source_csv)
        
        if limit:
            coordinates = coordinates[:limit]
        
        print(f"Found {len(coordinates)} coordinates for {gender}")
        
        # 各コーディネートを解析
        for i, coord in enumerate(coordinates):
            print(f"Processing {gender} coordinate {i+1}/{len(coordinates)} (ID: {coord['id']})")
            
            # 画像をダウンロード
            image_base64 = self.download_image(coord['image_url'])
            if not image_base64:
                continue
            
            # GPTで解析
            analysis = self.analyze_coordinate_with_gpt(image_base64, gender)
            if analysis:
                coord['analysis'] = analysis
                print(f"Analysis completed for ID: {coord['id']}")
            else:
                print(f"Analysis failed for ID: {coord['id']}")
        
        # CSVを更新
        self.update_csv_with_analysis(target_csv, coordinates)
        print(f"Completed processing {gender} coordinates")
    
    def run(self, limit_per_gender: Optional[int] = None):
        """メイン処理を実行"""
        print("Starting coordinate analysis...")
        
        # CSVファイルをコピー
        self.copy_csv_files()
        
        # women と men を処理
        self.process_gender("women", limit_per_gender)
        self.process_gender("men", limit_per_gender)
        
        print("Coordinate analysis completed!")

if __name__ == "__main__":
    # 使用例: 各性別の最初の5件のみテスト実行
    analyzer = CoordinateAnalyzer()
    analyzer.run(limit_per_gender=5)