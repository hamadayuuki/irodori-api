import requests
from bs4 import BeautifulSoup

# 指定されたURLへアクセスする
url = 'https://zozo.jp/search/?sex=men&p_keyv=%94%92T%83V%83%83%83c'


# ページのHTMLを取得する
response = requests.get(url)

# ステータスコードを確認する
if response.status_code == 200:
    # HTMLの取得成功
    html_content = response.text

    # BeautifulSoupでHTMLをパース
    soup = BeautifulSoup(html_content, "html.parser")
    script_tag = soup.find("script", {"id": "__NEXT_DATA__"})

    # 2. JSON文字列を辞書型に変換
    json_str = script_tag.string  # scriptタグの中身を取得
    data = json.loads(json_str)
    print(data)

    # # 3. 画像URLを格納するリスト
    # image_urls = []

    # # すべての階層を再帰的に探索し、"url"キーがあれば取得する関数
    # def find_urls(obj):
    #     if isinstance(obj, dict):
    #         for k, v in obj.items():
    #             # キーが"url"かつ値が文字列の場合に画像URLとみなす
    #             if k == "url" and isinstance(v, str):
    #                 image_urls.append(v)
    #             else:
    #                 find_urls(v)
    #     elif isinstance(obj, list):
    #         for item in obj:
    #             find_urls(item)

    # # 再帰的に検索
    # find_urls(data)

    # # 結果表示
    # for idx, url in enumerate(image_urls, 1):
    #     print(f"{idx}: {url}")


else:
    print(f'ページの取得に失敗しました。ステータスコード: {response.status_code}')

