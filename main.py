import os
import base64
import json
from typing import List
import urllib
import random

from pydantic import BaseModel
import requests

from fastapi import FastAPI
app = FastAPI()

from openai import OpenAI
client = OpenAI(
    api_key = os.getenv('OPENAI_API_KEY')
)
gptModel = "gpt-4o-mini"

@app.get("/")
async def root():
    return {"message": "Hello, FastAPI on Render!"}

@app.get("/check-gpt")
async def checkGPT():
    completion = client.chat.completions.create(
        model = gptModel,
        messages=[{
            "role": "user",
            "content": "Write a one-sentence bedtime story about a unicorn."
        }]
    )
    return {"result": completion.choices[0].message.content}

@app.get("/check-vision-gpt")
async def checkVisionGPT():
    imageURL = "https://images.wear2.jp/coordinate/DZiOeg3/21k0twHn/1728043950_500.jpg"   # WEARのコーデ画像
    imageData = requests.get(imageURL).content
    encodedImage = base64.b64encode(imageData).decode('utf-8')
    prompt = """
    添付する画像に合わせて、以下の質問に回答する形でコーデに関するコメントをください。

    ## フォーマット
    - ワンポイントアイテムを褒める <褒める>
    例 : 白色のキャップが可愛いですね
    - サイズ感についてのコメント
    例 : ワイドなパンツを履いているのでラフでスマートな印象を受けます。\n上下のサイズがちょうど良いのでおしゃれな印象を受けます
    - シルエット診断 <知見の共有>
    例 : あなたのシルエットはIです。Iが似合うのは〜のような特徴を持った方です
    - コーディネートタイプ診断 <知見の共有>
    例 : また、あなたのコーデはカジュアルです。
    - あなたに似合うコーディネートタイプは
    例 : カジュアル が似合う方におすすめのコーデタイプは、ノームコアです。
    
    ## アウトプットのフォーマット（必ず文字列のみでアウトプットしてください）
    <ワンポイントアイテムを褒める>\n
    <サイズ感についてのコメント>\n
    <シルエット診断>\n
    <コーディネートタイプ診断>\n
    <あなたに似合うコーディネートタイプは>\n
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encodedImage}"
                        }
                    }
                ]
            }
        ],
        max_tokens=300,
    )
    return {"result": response.choices[0].message.content}


class ImageRequest(BaseModel):
    image_base64: str
class ImageResponse(BaseModel):
    coordinate_review: str
    coordinate_item01: str
    recommend_item01: str
    coordinate_item02: str
    recommend_item02: str
    coordinate_item03: str
    recommend_item03: str


class CoordinateResponse(BaseModel):
    id: int
    coordinate_review: str
    coordinate_item01: str
    recommend_item01: str
    recommend_item01_url: str
    coordinate_item02: str
    recommend_item02: str
    recommend_item02_url: str
    coordinate_item03: str
    recommend_item03: str
    recommend_item03_url: str


@app.post("/coordinate-review", response_model = CoordinateResponse)
async def coordinateReview(request: ImageRequest):
    gender = "men"   # TODO: 動的化

    solver = """
    あなたはプロのファッションコーディネータです。
    豊富な経験と鋭い観察力で、与えられたコーデ画像をもとに、ユーザーの服装を分析し、着こなし方や色の組み合わせ、シルエットやサイズ感など、的確で具体的なアドバイスを提供します。
    また、トレンド感のあるアイテムやスタイル提案にも精通しており、コーデ画像から季節感を考慮し、ユーザーの魅力を引き出す最適なコーディネートを提案できます。
    """
    prompt = """
    添付する画像に合わせて、アウトプットを生成してください.
    アウトプットはJSON形式です。Valueは全てString型ですので、" で囲んでください。<> は動的データを示します。
    アウトプットがJSONの形式になっているか、ステップバイステップで確認してから、返答してください。

    ## coordinate_review について
    以下のフォーマットと出力例をもとに、300文字程度アウトプットしてください

    ## coordinate_review のフォーマット(必ずこのフォーマット通りに出力してください)
    <誰も気づかないようなワンポイントアイテムを褒める>
    <サイズ感についてのコメント>
    <シルエット診断>
    <コーディネートタイプ診断>
    <あなたのボトムスに合うトップスは>
    <あなたのトップスに合うボトムスは>

    ## coordinate_review の出力例
    白色のキャップが可愛いですね
    ワイドなパンツを履いているのでラフでスマートな印象を受けます。\n上下のサイズがちょうど良いのでおしゃれな印象を受けます
    あなたのシルエットはIです。Iが似合うのは〜のような特徴を持った方です
    また、あなたのコーデのタイプはカジュアルです。
    あなたの履いている黒色のワイドパンツに合うトップスはグレーのスウェットです。ワイドパンツなのでスウェットのサイズは少し小さめ良さそうです。
    また、あなたの着ているカーキの長袖シャツに合うボトムスは、黒色のカーゴパンツです。カーゴパンツはラフになりすぎるので、色は落ち着いた黒色をおすすめします。

    ## coordinate_item01 について
    コーデで使われているアイテムをピックアップしてください。(coordinate_item02,03 でピックアップしたアイテムと重複してはいけない)
    ピックアップしたアイテムについて述べてください。
    ## coordinate_item01 出力例（ピックアップしたアイテムと別なアイテムをおすすめしてください。トップスをピックアップして、トップスをおすすめしてはいけません。）
    黒色のスラックスパンツに合うのは...

    ## recommend_item01 について
    coordinate_item01 でピックアップしたアイテムに合う、おすすめするアイテムを下記のように出力してください
    ## recommend_item01 出力例（です。ます。を使わない）
    花柄 長袖シャツ


    ## coordinate_item02,03 について
    coordinate_item01 を参考にして出力してください。01,02,03 でアイテムが重複しないようにしてください。
    ## recommend_item02,03 について
    recommend_item01 を参考にして出力してください


    ## アウトプットのフォーマット（JSON形式でアウトプアットを生成してください）
    {
        "coordinate_review": "<coordinate_review>",
        "coordinate_item01": "<coordinate_item01>",
        "recommend_item01": "<recommend_item01>",
        "coordinate_item02": "<coordinate_item02>",
        "recommend_item02": "<recommend_item02>",
        "coordinate_item03": "<coordinate_item03>",
        "recommend_item03": "<recommend_item03>",
    }
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": solver,
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{request.image_base64}"
                        }
                    }
                ]
            }
        ],
        response_format = {"type": "json_object"},
        max_tokens = 1000,
    )
    print(response.choices[0].message.content)

    openAIResponse = response.choices[0].message.content
    openAIResponseJSON = json.loads(openAIResponse)
    imageResponse = ImageResponse(**openAIResponseJSON)


    coordinate_item02: str
    recommend_item02: str
    recommend_item02_url: str
    coordinate_item03: str
    recommend_item03: str
    recommend_item03_url: str

    coordinateResponse = CoordinateResponse(
        id = random.randrange(10**10),

        coordinate_review = imageResponse.coordinate_review,   # coordinate_review

        coordinate_item01 = imageResponse.coordinate_item01,   # coordinate_item01
        recommend_item01 = imageResponse.recommend_item01,   # recommend_item01
        recommend_item01_url = f"https://zozo.jp/search/?sex={gender}&p_keyv={urllib.parse.quote(imageResponse.recommend_item01, encoding='shift_jis')}",   # recommend_item01_url

        coordinate_item02 = imageResponse.coordinate_item02,
        recommend_item02 = imageResponse.recommend_item02,
        recommend_item02_url = f"https://zozo.jp/search/?sex={gender}&p_keyv={urllib.parse.quote(imageResponse.recommend_item02, encoding='shift_jis')}",

        coordinate_item03 = imageResponse.coordinate_item03,
        recommend_item03 = imageResponse.recommend_item03,
        recommend_item03_url = f"https://zozo.jp/search/?sex={gender}&p_keyv={urllib.parse.quote(imageResponse.recommend_item03, encoding='shift_jis')}"
    )
    print(coordinateResponse)

    return coordinateResponse



