#!/usr/bin/env python3
import csv
import sys
import os
import pandas as pd
from dataclasses import dataclass

@dataclass
class AnimalFortuneResult:
    """動物占い結果を格納するデータクラス"""
    base_personality: str
    life_tendency: str
    female_feature: str
    male_feature: str
    love_tendency: str

def load_calendar_data():
    """calendar.csvを読み込んで辞書形式で返す"""
    calendar_data = {}
    # 現在のファイルのディレクトリを基準にCSVファイルのパスを構築
    csv_path = os.path.join(os.path.dirname(__file__), 'calendar.csv')
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # ヘッダー行を読み込み
        
        for row in reader:
            year = int(row[0])
            calendar_data[year] = {}
            for i, month_value in enumerate(row[1:], 1):
                calendar_data[year][i] = int(month_value)
    return calendar_data

def load_animal_data():
    """animals.csvを読み込んで辞書形式で返す"""
    animals = {}
    # 現在のファイルのディレクトリを基準にCSVファイルのパスを構築
    csv_path = os.path.join(os.path.dirname(__file__), 'animals.csv')
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            no = int(row['index'])
            animals[no] = {
                'animal': row['animal'],
                'character': row['animal_name'],
                'link': row['link']
            }
    return animals

def parse_input(input_str):
    """入力文字列を解析してYYYYMMDDから年月日を取得"""
    # 最初の8桁を使用（9桁目があっても無視）
    date_part = input_str[:8]
    
    if len(date_part) != 8:
        raise ValueError("入力は8桁以上の数字である必要があります")
    
    year = int(date_part[:4])
    month = int(date_part[4:6])
    day = int(date_part[6:8])
    
    return year, month, day

def calculate_animal_number(year, month, day, calendar_data):
    """動物番号を計算"""
    if year not in calendar_data:
        raise ValueError(f"年 {year} はサポートされていません（1926-2030年のみ）")
    
    if month not in calendar_data[year]:
        raise ValueError(f"月 {month} が無効です")
    
    # 1. calendar.csvから年月の交差点の値を取得
    fortune_num = calendar_data[year][month]
    
    # 2. animalNum = fortuneNum + day（60を超えたら60を引く）
    animal_num = fortune_num + day
    if animal_num > 60:
        animal_num -= 60
    
    # 0になった場合は60にする（1-60の範囲）
    if animal_num == 0:
        animal_num = 60
    
    return animal_num

def animal_fortune(year, month, day) -> AnimalFortuneResult:
    """動物占いを実行し、結果を返す"""
    input_str = str(year) + str(month).zfill(2) + str(day).zfill(2)   # YYYYMMDD
    
    # データ読み込み
    calendar_data = load_calendar_data()
    animals = load_animal_data()
    
    # 入力解析
    year, month, day = parse_input(input_str)
    
    # 動物番号計算
    animal_number = calculate_animal_number(year, month, day, calendar_data)
    
    # 占い結果取得
    # 現在のファイルのディレクトリを基準にCSVファイルのパスを構築
    csv_path = os.path.join(os.path.dirname(__file__), 'animal_feature.csv')
    df = pd.read_csv(csv_path)
    base_personality = df.iloc[animal_number - 1, 2]  # indexは0ベースなので-1
    life_tendency = df.iloc[animal_number - 1, 3]
    female_feature = df.iloc[animal_number - 1, 4]
    male_feature = df.iloc[animal_number - 1, 5]
    love_tendency = df.iloc[animal_number - 1, 6]
    
    return AnimalFortuneResult(
        base_personality=base_personality,
        life_tendency=life_tendency,
        female_feature=female_feature,
        male_feature=male_feature,
        love_tendency=love_tendency
    )

def main():
    """メイン関数（従来のCLI機能）"""
    if len(sys.argv) != 2:
        print("使用法: python animal_fortune.py [数字]")
        print("例: python animal_fortune.py 200101125")
        sys.exit(1)
    
    input_str = sys.argv[1]
    
    try:
        # 入力解析
        year, month, day = parse_input(input_str)
        
        # 動物占い実行
        result = animal_fortune(year, month, day)
        
        # 結果出力
        print("=== 動物占い結果 ===")
        print(f"基本性格: {result.base_personality}")
        print(f"人生傾向: {result.life_tendency}")
        print(f"女性特徴: {result.female_feature}")
        print(f"男性特徴: {result.male_feature}")
        print(f"恋愛傾向: {result.love_tendency}")
        
    except Exception as e:
        print(f"エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()