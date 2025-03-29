import os
import base64
import json
from typing import List

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
    result: str


class CoordinateResponse(BaseModel):
    coordinate_review: str


@app.post("/coordinate-review", response_model = ImageResponse)
async def coordinateReview(request: ImageRequest):
    solver = """
    あなたはプロのファッションコーディネータです。
    豊富な経験と鋭い観察力で、与えられたコーデ画像をもとに、ユーザーの服装を分析し、着こなし方や色の組み合わせ、シルエットやサイズ感など、的確で具体的なアドバイスを提供します。
    また、トレンド感のあるアイテムやスタイル提案にも精通しており、コーデ画像から季節感を考慮し、ユーザーの魅力を引き出す最適なコーディネートを提案できます。
    """
    prompt = """
    添付する画像に合わせて、以下の質問に回答する形でコーデに関するコメントをください。

    ## coordinateReviewのフォーマット
    <ワンポイントアイテムを褒める>
    <サイズ感についてのコメント>
    <シルエット診断>
    <コーディネートタイプ診断>
    <あなたに似合うコーディネートタイプは>

    ## coordinateReviewの出力例
    白色のキャップが可愛いですね
    ワイドなパンツを履いているのでラフでスマートな印象を受けます。\n上下のサイズがちょうど良いのでおしゃれな印象を受けます
    あなたのシルエットはIです。Iが似合うのは〜のような特徴を持った方です
    また、あなたのコーデはカジュアルです。
    カジュアル が似合う方におすすめのコーデタイプは、ノームコアです。

    
    ## アウトプットのフォーマット（JSON形式でアウトプアットを生成してください）
    {
        "coordinate_review": "<coordinateReviewのフォーマットに従って生成してください。また、coordinateReviewの出力例を参考にしてください。出力例よりもクオリティーの高い、本質的な文章を生成してください。: String型>",
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
        max_tokens = 300,
    )
    print(response.choices[0].message.content)


    openAIResponse = response.choices[0].message.content
    openAIResponseJSON = json.loads(openAIResponse)
    coordinateResponse = CoordinateResponse(**openAIResponseJSON)
    print(coordinateResponse)

    return ImageResponse(result = coordinateResponse.coordinate_review)


