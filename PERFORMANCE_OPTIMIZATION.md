# /recommend-coordinates エンドポイント パフォーマンス最適化

## 問題
- レスポンス時間: 約30秒
- 原因: Yahoo Shopping APIの同期的な呼び出し（最大6回）

## 実装した改善

### 1. 非同期処理の導入
- `aiohttp`ライブラリを使用した非同期HTTPクライアント
- `asyncio.gather()`による並行API呼び出し
- タイムアウトを10秒から5秒に短縮

### 主な変更ファイル
1. `requirements.txt`: `aiohttp`追加
2. `yahoo_shopping.py`: `search_products_async()`メソッド追加
3. `coordinate_service.py`: `recommend_coordinates_async()`メソッド追加
4. `main.py`: 非同期メソッドの使用

### 期待される効果
- レスポンス時間: 30秒 → 5-8秒
- 並行処理により、最も遅いAPI呼び出しの時間でレスポンス可能

## テスト方法

```bash
# サーバー起動
uvicorn main:app --reload

# パフォーマンステスト実行
python test_performance.py
```

## 今後の改善案

### フェーズ2: キャッシュの実装
- CSVデータの起動時キャッシュ
- Yahoo API結果のメモリキャッシュ（TTL: 1時間）

### フェーズ3: データ構造の最適化
- CSVの重複読み込み排除
- ジャンル情報の統合

### フェーズ4: 追加最適化
- Redisキャッシュの導入
- CDNの活用
- データベースへの移行