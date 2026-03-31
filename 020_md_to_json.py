"""
020_md_to_json.py の処理概要

- 入力:
    - PROJECT_DIR 配下の cu_md フォルダにある Markdown ファイル群
    - 環境変数 PROJECT_DIR / AZURE_OPENAI_API_ENDPOINT / AZURE_OPENAI_MODEL / FILTER_MODEL_DEPLOYMENT
- 主処理:
    1) Entra 認証で Azure OpenAI クライアントを初期化
    2) Markdown の本文を読み込み、LLM でタイトル・要約・キーワードを抽出
    3) フィルター（会社名/業務名）を抽出し、ページ情報などのメタデータを付与
    4) 1ファイルごとに JSON として保存
- 出力:
    - PROJECT_DIR 配下の md_json/*.json

補足:
- 出力 JSON が既に存在する場合はスキップする。
- 必須環境変数が未設定の場合は RuntimeError で終了する。
"""

import os
import json
import re
import pandas as pd
from pathlib import Path

from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv  

# 環境変数を読み込む  
load_dotenv() 

PROJECT_DIR = os.getenv("PROJECT_DIR", "").strip()
if not PROJECT_DIR:
    raise RuntimeError("PROJECT_DIR is not set.")

# Azure OpenAI Service の情報を環境変数から取得する
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_API_ENDPOINT")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL")
FILTER_MODEL_DEPLOYMENT = os.getenv("FILTER_MODEL_DEPLOYMENT")

# Entra認証でOpenAIクライアントを初期化
if not AZURE_OPENAI_ENDPOINT:
    raise RuntimeError("AZURE_OPENAI_API_ENDPOINT is not set.")

if not AZURE_OPENAI_MODEL:
    raise RuntimeError("AZURE_OPENAI_MODEL is not set.")

if not FILTER_MODEL_DEPLOYMENT:
    raise RuntimeError("FILTER_MODEL_DEPLOYMENT is not set.")

credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")

client = OpenAI(
    base_url=AZURE_OPENAI_ENDPOINT,
    api_key=token_provider,
)

# フィルターを抽出する関数 会社名や業務名など
def get_filter(content, source_file_name=""):
    """コンテンツから会社名または業務名を抽出する。見つからない場合は n/a を返す。"""
    def _extract_name(target_text, source_label):
        if not target_text or not str(target_text).strip():
            return "n/a"

        system_context = (
            "あなたは文書から会社名または業務名を抽出するアシスタントです。"
            "必ず最も代表的な1つだけ返してください。"
            "会社名を優先し、無ければ業務名を返してください。"
            "説明文や記号は付けず、値だけを返してください。"
            "判別できない場合のみ n/a を返してください。"
        )
        user_request = (
            f"次の{source_label}から会社名または業務名を抽出してください。\n"
            "- 優先順: 会社名 > 業務名\n"
            "- 回答は値のみ（1つ）\n"
            "- 不明な場合は n/a\n\n"
            f"{source_label}:\n{str(target_text)}"
        )

        response = client.responses.create(
            model=FILTER_MODEL_DEPLOYMENT,
            input=[
                {"role": "system", "content": system_context},
                {"role": "user", "content": user_request},
            ],
        )

        extracted = response.output[0].content[0].text.strip()
        extracted = extracted.strip('"').strip("'").strip()
        return extracted or "n/a"

    def _normalize(value):
        if not value:
            return ""
        return re.sub(r"[\s\-ー_・\.\(\)\[\]{}『』「」]", "", str(value).lower())

    file_base_name = re.sub(r"_p\d+$", "", source_file_name or "")
    company_from_filename = _extract_name(file_base_name, "ファイル名")
    company_from_content = _extract_name(content, "本文")

    if company_from_filename != "n/a":
        if company_from_content != "n/a" and _normalize(company_from_filename) != _normalize(company_from_content):
            print(f"[Filter] Mismatch detected. filename='{company_from_filename}', content='{company_from_content}'. Use filename.")
        return company_from_filename

    return company_from_content if company_from_content != "" else "n/a"


# フィルターを抽出する関数 会社名や業務名など
def get_sub_filter(content):
    """コンテンツからxxxxを抽出する（簡易版）"""
    # 必要であれば実装する
    return "n/a"


# ドキュメントの要約、キーワードを抽出する関数
def get_info(context):

    # systemコンテキストを定義
    system_context = """あなたは優秀なアシスタントです。社内にあるドキュメントの内容を読み解き、わかりやすく要約し、キーワードを抽出します。\
ナレッジベースを作成して、RAGに活用していきます。以下の制約条件と形式を守って、JSON形式で出力してください。\
###制約条件\
- 与えられるコンテキストは、ドキュメントをチャンクした文章です。与えられたチャンクの部分を要約し、summaryの値として出力します。要約した内容には、重要なキーワードは含めるようにしてください。\
- 与えられたチャンクの文章に対して1文でタイトルを付与します。titleの値として出力します。 \
- 本チャンク内で検索に活用する重要なキーワードを抽出する。キーワードは25個以内とします \
- 出力形式を守ります \
###出力形式\
summary: <チャンクした部分を要約した内容>\
title: <チャンクした部分のタイトル>\
Keywords: ["keyword1", "Keyword2", ...]  """

    # ユーザリクエストを定義
    user_request = "以下のコンテキストから制約条件と出力形式を必ず守って、JSON形式で出力をしてください。最初から最後まで注意深く読み込んでください。\
最高の仕事をしましょう。あなたならできる！\
###コンテキスト" + str(context)

    #Json配列を作成
    messages = []
 
    #messagesに要素を追加
    messages.append({"role": "system", "content": system_context})
    messages.append({"role": "user", "content": user_request})

    # response = client.chat.completions.create(
    #     model=AZURE_OPENAI_MODEL, 
    #     messages=messages,
    #     # temperature=0.0,
    #     # max_tokens=AZURE_OPENAI_CHAT_MAX_TOKENS,
    #     response_format={ "type": "json_object" },
    # )
    response = client.responses.create(
        model=AZURE_OPENAI_MODEL,
        input=messages,
    )

    # レスポンスからテキストを抽出
    response_text = response.output[0].content[0].text
    
    # ```json ... ``` のマークダウンコードブロックを削除
    if response_text.startswith('```json'):
        response_text = response_text.strip('```json').strip('```').strip()
    
    # JSONとしてパース
    content = json.loads(response_text)
    
    # Extract information from the content
    doc_info = {}
    doc_info['title'] = content['title']
    doc_info['summary'] = content['summary']
    doc_info['Keywords'] = content['Keywords']
    
    return doc_info


def md_to_json_run(md_path, file_name,json_file_path):
    """マークダウンファイルをJSONに変換する関数"""
    # 既存のJSONファイルがある場合はスキップ
    if os.path.exists(json_file_path/f"{file_name}.json"):
        print(f"スキップ: {file_name}.json は既に存在します")
        return
    
    # マークダウンファイルを読み込み
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # ファイル名からベース名とページ番号を抽出
    # フォーマット: ファイル名_p01
    match = re.search(r'_p(\d+)$', file_name)
    if match:
        base_file_name = file_name[:match.start()]
        page_number = match.group(1)
    else:
        base_file_name = file_name
        page_number = '0'
    
    # フィルターを取得
    filter = get_filter(content, file_name)
    content_with_filter = f"# {filter}に関するナレッジ\n{content}"

    # データ構造を作成
    data = [{
        'id': file_name,
        'file_name': base_file_name,
        'page': page_number,
        'content': content_with_filter,
        'title': '',
        'summary': '',
        'keywords': []
    }]
    
    # DataFrameに変換
    df = pd.json_normalize(data)
    
    df.insert(2, 'filter', filter)

    # サブフィルターを取得
    sub_filter = get_sub_filter(content)
    df.insert(3, 'sub_filter', sub_filter)

    # AzureOpenAIによる情報付加
    for index, row in df.iterrows():
        docinfo = get_info(row['content'])
        df.at[index, 'title'] = docinfo['title']
        df.at[index, 'summary'] = filter + "\n" + sub_filter + "\n" + docinfo['summary']
        df.at[index, 'keywords'] = docinfo['Keywords']
    
    # JSONファイルとして保存
    output_file = json_file_path / f"{file_name}.json"
    df.to_json(output_file, force_ascii=False, orient='records')
    print(f"JSONファイル出力: {output_file}")

if __name__ == "__main__":
    # doc_mdフォルダ内の全てのマークダウンファイルを処理
    md_folder = "doc_md"
    # md_folder = "test_md"
    BASE_DIR = Path(__file__).resolve().parent
    MD_DIR = BASE_DIR / PROJECT_DIR / "cu_md"
    OUT_DIR = BASE_DIR / PROJECT_DIR / "md_json"
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # di_md
    md_files = list(MD_DIR.glob("*.md"))
    
    if not md_files:
        print(f"No MD files found in {MD_DIR}")
    else:
        print(f"Found {len(md_files)} MD file(s) to process")
        
        for IN_MD in md_files:
            output_json = OUT_DIR / f"{IN_MD.stem}.json"
            if output_json.exists():
                print(f"\nSkip: output already exists -> {output_json}")
                continue

            print(f"\nProcessing: {IN_MD.name}")
            
            md_to_json_run(IN_MD, IN_MD.stem, OUT_DIR)

            # break  # テスト用に最初の1ファイルのみ処理
        
        print(f"\nCompleted processing {len(md_files)} MD file(s)")

    # # マークダウンファイルを検索
    # for root, dirs, files in os.walk(md_folder):
    #     for file in files:
    #         if file.lower().endswith('.md'):
    #             md_path = os.path.join(root, file)
    #             file_name = os.path.splitext(file)[0]  # 拡張子を除去
                
    #             print(f"処理中: {md_path}")
    #             md_to_json(md_path, file_name)
    
