"""
050_create_index.py の処理概要

- 入力:
    - PROJECT_DIR 配下の merged_vector_json/vector.json（投入対象ドキュメント）
    - index.json（インデックス定義）
    - 環境変数 AI_SEARCH_ENDPOINT / AI_SEARCH_INDEX_NAME / PROJECT_DIR
- 主処理:
    1) Entra 認証で Azure AI Search に接続
    2) 既存インデックスの存在確認と削除（存在する場合）
    3) index.json からインデックスを作成
    4) vector.json からドキュメントを読み込み、バッチでアップロード
- 出力:
    - 指定インデックスへのドキュメント登録
権限要件（Entra 認証）:
- Search Service Contributor（インデックス作成・削除） *最新では不要の場合あり
- Search Index Data Contributor（ドキュメント投入）
"""

import json
import os
import hashlib
from pathlib import Path
import requests
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient

from dotenv import load_dotenv  

# 環境変数を読み込む  
load_dotenv() 


PROJECT_DIR = os.getenv("PROJECT_DIR", "").strip()
if not PROJECT_DIR:
    raise RuntimeError("PROJECT_DIR is not set.")

# Azure AI Search の情報を環境変数から取得する
AI_SEARCH_ENDPOINT = os.getenv("AI_SEARCH_ENDPOINT", "").strip()
AI_SEARCH_API_VERSION = os.getenv("AI_SEARCH_API_VERSION", "2023-10-01-Preview")

if not AI_SEARCH_ENDPOINT:
    raise RuntimeError("AI_SEARCH_ENDPOINT is not set.")

# Azure AI Search のクライアントを作成する
credential = DefaultAzureCredential()
index_client = SearchIndexClient(
    endpoint=AI_SEARCH_ENDPOINT,
    credential=credential,
)

# インデックスが存在するか確認する
def check_index_exists(name):
    print(f"index_name:{name}")
    try:
        index_client.get_index(name)
        return True
    except ResourceNotFoundError:
        return False

# インデックスを削除する
def delete_index(name):
    index_client.delete_index(name)

# インデックスを作成する
def create_index(name, json_file_path):
    with open(json_file_path, "r", encoding='utf-8') as f:
        data = json.load(f)
    
    # インデックス名を設定
    data["name"] = name
    
    access_token = credential.get_token("https://search.azure.com/.default").token
    resp = requests.post(
        f"{AI_SEARCH_ENDPOINT}/indexes?api-version={AI_SEARCH_API_VERSION}",
        data=json.dumps(data),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
    )
    if not str(resp.status_code).startswith("2"):
        raise Exception(resp.text)  # 2xx 以外の場合はエラー
    return resp.status_code

# インデックスにドキュメントを追加する
def add_documents(index_name, docs):
    search_client = SearchClient(
        endpoint=AI_SEARCH_ENDPOINT,
        credential=credential,
        index_name=index_name,
    )
    search_client.upload_documents(documents=docs)


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    VECTOR_JSON_DIR = BASE_DIR / PROJECT_DIR / "merged_vector_json"
    index_def_path = Path.cwd() / "index.json"
    index_name = os.getenv("AI_SEARCH_INDEX_NAME")
    if not index_name:
        print("エラー: AI_SEARCH_INDEX_NAME が .env に設定されていません")
        exit(1)

    # JSONデータ（ファイルから読み込む場合）
    json_file_path = VECTOR_JSON_DIR / 'vector.json'
    index_docs = []

    if not json_file_path.exists():
        print(f"エラー: {json_file_path} が存在しません")
        exit(1)

    with open(json_file_path, 'r', encoding='utf-8') as file:
        json_data = json.load(file)

        for data in json_data:
            id_hash = hashlib.sha256(data['id'].encode('utf-8')).hexdigest()
            index_doc = {
                "id" :id_hash,
                "fileName" : data['file_name'],
                "filter" : data['filter'],
                "sub_filter" : data['sub_filter'],
                "page" : data['page'],
                "content" : data['content'],
                "title" : data['title'],
                "summary" : data['summary'],
                "keywords" : data['keywords'],
                "contentVector" : data['vector'],
            }

            index_docs.append(index_doc)

    if not index_def_path.exists():
        print(f"エラー: {index_def_path} が存在しません")
        exit(1)
    
    ## Azure AI Search にインデックスを作成
    if check_index_exists(index_name):
        print("delete index:", index_name)
        delete_index(index_name)

    print("create index:", index_name)
    create_index(index_name, index_def_path)



    ## インデックスにドキュメントを追加
    print("upload documents to index:", index_name)
    print(f"Total documents: {len(index_docs)}")


    batch=500 #n文書単位でindexを作成する
    for i in range(0,len(index_docs),batch):
        if i+batch<len(index_docs):
            add_documents(index_name, index_docs[i:i+batch])  
            print(f"Uploaded {i}-{i+batch} content") 
        
    add_documents(index_name, index_docs[i:len(index_docs)])  
    print(f"Uploaded {i}-{len(index_docs)} content") 

    print("\nCompleted index creation and document upload")


