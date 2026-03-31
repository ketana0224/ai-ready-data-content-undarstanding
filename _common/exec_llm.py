import os
import re
import json
import collections
import logging
import csv
import string
import tempfile
from datetime import datetime
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
# 環境変数を読み込む
load_dotenv()


from azure.core.credentials import AzureKeyCredential


# envファイルから環境変数を取得
# GPT-5 model
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_API_ENDPOINT") or os.getenv("FDPO_AZURE_OPENAI_API_ENDPOINT")
AOAI_GA_DEPLOYMENT = 'gpt-5.2'
AOAI_CHAT_GA_DEPLOYMENT = 'gpt-5.2-chat'

def llm_run(question):  ##複雑な質問を分割する関数
    if not AZURE_OPENAI_ENDPOINT:
        raise ValueError("AZURE_OPENAI_API_ENDPOINT または FDPO_AZURE_OPENAI_API_ENDPOINT が未設定です。")

    # Azure OpenAI のクライアントを作成する
    client = OpenAI(
        base_url=AZURE_OPENAI_ENDPOINT,
        api_key=get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default",
        ),
    )

    messagestemp = []
    messagestemp.append({"role": "system", "content": "あなたはAIアシスタントです。\n# 指示に忠実に従ってください。"})
    messagestemp.append({"role": "user", "content": question})

    response = client.responses.create(
        model=AOAI_GA_DEPLOYMENT,
        input=messagestemp,
    )

    result = response.output[0].content[0].text
    return(result)
              

if __name__ == '__main__':
    # ユーザからの入力を取得する
    user_input = "こんにちは"
    print(llm_run(user_input))
else:
    None
