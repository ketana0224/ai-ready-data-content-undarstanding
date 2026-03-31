"""
030_json_add_vector.py の処理概要

- 入力:
    - PROJECT_DIR 配下の md_json フォルダにある JSON ファイル群
    - 環境変数 PROJECT_DIR / AZURE_OPENAI_API_ENDPOINT / AZURE_OPENAI_EMBED_MODEL
- 主処理:
    1) Entra 認証で Azure OpenAI クライアントを初期化
    2) 各 JSON を読み込み、行ごとに埋め込みベクトルを生成
       - summary があれば summary を優先
       - なければ content を使用
    3) 生成したベクトルを vector 列として追加
    4) vector_json フォルダに同名 JSON として保存
- 出力:
    - PROJECT_DIR 配下の vector_json/*.json

補足:
- 既存の出力ファイルがある場合はスキップする。
- PROJECT_DIR や Azure OpenAI 関連環境変数が未設定の場合は RuntimeError で終了する。
"""

import os
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
# AZURE_OPENAI_MODEL = 'gpt-5.2'
AOAI_EMBED_MODEL = os.getenv("AZURE_OPENAI_EMBED_MODEL")

if not AZURE_OPENAI_ENDPOINT:
    raise RuntimeError("AZURE_OPENAI_API_ENDPOINT is not set.")

if not AOAI_EMBED_MODEL:
    raise RuntimeError("AZURE_OPENAI_EMBED_MODEL is not set.")

credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")

client = OpenAI(
    base_url=AZURE_OPENAI_ENDPOINT,
    api_key=token_provider,
)



# client = AzureOpenAI(
#     azure_endpoint=os.getenv("IDX_AZURE_OPENAI_ENDPOINT"),
#     api_key=os.getenv("IDX_AZURE_OPENAI_API_KEY"),
#     api_version=os.getenv("IDX_AZURE_OPENAI_API_VERSION")
# )

# Azure OpenAI Service によるベクトル生成
def get_vector(content):
    resp = client.embeddings.create(model=AOAI_EMBED_MODEL, input=content)
    return resp.data[0].embedding

def process_json_file(json_path, output_path):
    """単一のJSONファイルを処理してベクトルを追加"""
    print(f"処理中: {json_path}")
    # 既存のJSONファイルがある場合はスキップ
    if os.path.exists(output_path):
        print(f"スキップ: {output_path} は既に存在します")
        return
        
    # JSONデータをDataFrameに変換
    df = pd.read_json(json_path)
    
    # DataFrameの項目追加
    df.insert(len(df.columns), 'vector', None)
    
    # 条件に基づいてデータを更新
    for index, row in df.iterrows():
        # summaryがある場合はそれを使用、なければcontentを使用
        text_content = row.get('summary', '') if row.get('summary', '') else row.get('content', '')
        if text_content:
            df.at[index, 'vector'] = get_vector(text_content)
        else:
            print(f"警告: {json_path} のインデックス {index} にはベクトル化可能なコンテンツがありません")
    
    # 結果を保存
    df.to_json(output_path, force_ascii=False, orient='records')
    print(f"ベクトル付きJSONファイル出力: {output_path}")

if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    IN_DIR = BASE_DIR / PROJECT_DIR / "md_json"
    OUT_DIR = BASE_DIR / PROJECT_DIR / "vector_json"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # JSONファイルを取得
    json_files = list(IN_DIR.glob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {IN_DIR}")
    else:
        print(f"Found {len(json_files)} JSON file(s) to process")
        
        for IN_JSON in json_files:
            print(f"\nProcessing: {IN_JSON.name}")
            
            output_path = OUT_DIR / IN_JSON.name
            
            # 既に出力ファイルが存在する場合はスキップ
            if output_path.exists():
                print(f"スキップ（既存ファイル）: {output_path}")
                continue
            
            try:
                process_json_file(IN_JSON, output_path)
            except Exception as e:
                print(f"エラー: {IN_JSON} の処理中にエラーが発生しました: {e}")

            # break  # テスト用に最初の1ファイルのみ処理
        
        print(f"\nCompleted processing {len(json_files)} JSON file(s)")

