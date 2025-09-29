import asyncio
import aiohttp
import time
import json

async def test_recommend_coordinates():
    url = "http://localhost:8000/recommend-coordinates"
    headers = {"Content-Type": "application/json"}
    data = {"gender": "men"}
    
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as response:
            result = await response.json()
            elapsed_time = time.time() - start_time
            
            print(f"\n=== Performance Test Result ===")
            print(f"Status Code: {response.status}")
            print(f"Response Time: {elapsed_time:.2f} seconds")
            print(f"Number of coordinates: {len(result.get('coordinates', []))}")
            
            # 各コーディネートのアフィリエイト商品数を確認
            for i, coord in enumerate(result.get('coordinates', [])):
                tops_count = len(coord.get('affiliate_tops', []))
                bottoms_count = len(coord.get('affiliate_bottoms', []))
                print(f"Coordinate {i+1}: {tops_count} tops, {bottoms_count} bottoms")
            
            return elapsed_time

async def run_multiple_tests(n=3):
    print(f"Running {n} tests...")
    times = []
    
    for i in range(n):
        print(f"\nTest {i+1}:")
        elapsed = await test_recommend_coordinates()
        times.append(elapsed)
        
        # 次のテストまで少し待つ
        if i < n-1:
            await asyncio.sleep(2)
    
    print(f"\n=== Summary ===")
    print(f"Average response time: {sum(times)/len(times):.2f} seconds")
    print(f"Min response time: {min(times):.2f} seconds")
    print(f"Max response time: {max(times):.2f} seconds")

if __name__ == "__main__":
    # 単一テスト
    print("Testing /recommend-coordinates endpoint...")
    asyncio.run(test_recommend_coordinates())
    
    # 複数回テスト
    print("\n" + "="*50 + "\n")
    asyncio.run(run_multiple_tests(3))