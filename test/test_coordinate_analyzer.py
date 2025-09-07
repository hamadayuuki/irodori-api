#!/usr/bin/env python3
import os
import sys

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# chatgptディレクトリをパスに追加
chatgpt_dir = os.path.join(project_root, 'data', 'chatgpt')
sys.path.append(chatgpt_dir)

from data.chatgpt.coordinate_analyzer import CoordinateAnalyzer

def test_coordinate_analyzer():
    """coordinate_analyzer.pyのテスト実行"""
    print("=== Coordinate Analyzer Test ===")
    print(f"Project root: {project_root}")
    print(f"Working directory: {os.getcwd()}")
    
    # OpenAI API Keyの確認
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable is not set")
        print("Please set the API key and run again:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        return
    
    print(f"OpenAI API Key: {api_key[:20]}...")
    
    try:
        # CoordinateAnalyzerのインスタンスを作成
        analyzer = CoordinateAnalyzer()
        
        # テスト実行: 各性別の最初の2件のみ
        print("\nStarting test run with 2 items per gender...")
        analyzer.run(limit_per_gender=2)
        
        print("\n=== Test completed successfully! ===")
        
    except Exception as e:
        print(f"ERROR: Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_coordinate_analyzer()