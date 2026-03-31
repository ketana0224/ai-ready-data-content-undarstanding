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
from dotenv import load_dotenv
# 環境変数を読み込む
load_dotenv()


from azure.core.credentials import AzureKeyCredential


# envファイルから環境変数を取得
# GPT-5 model
AZURE_OPENAI_API_ENDPOINT = os.getenv("AZURE_OPENAI_API_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
# EXEC_AZURE_OPENAI_API_VERSION = os.getenv("EXEC_AZURE_OPENAI_API_VERSION")
GPT52_GA_DEPLOYMENT = 'gpt-5.1'
GPT52_CHAT_GA_DEPLOYMENT = 'gpt-5.1-chat'

def table_to_json_llm_run(question):  ##複雑な質問を分割する関数
    # Azure OpenAI のクライアントを作成する
    client = OpenAI(
        base_url=AZURE_OPENAI_API_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        # api_version=EXEC_AZURE_OPENAI_API_VERSION?
    )

    # Set ChatGPT parameters in sidebar
    # Temperature_temp = 0.0
    #Json形式のmessagestemp変数に代入する
    messagestemp = []
    messagestemp.append({"role": "system", "content": "以下の情報をJSON形式にしてください。改行やインデントを入れて見やすくしてください。"})
    messagestemp.append({"role": "user", "content": question})

    output = client.chat.completions.create(
            model=GPT52_GA_DEPLOYMENT,
            messages=messagestemp,
            # temperature=Temperature_temp,
            # max_tokens=4000,
    )

    result = output.choices[0].message.content
    return(result)
              

if __name__ == '__main__':
    # ユーザからの入力を取得する
    user_input = "こんにちは"
    print(run(user_input))

