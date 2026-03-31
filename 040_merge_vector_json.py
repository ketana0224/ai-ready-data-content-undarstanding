"""
040_merge_vector_json.py の処理概要

- 入力:
    - PROJECT_DIR 配下の vector_json フォルダ内にある JSON ファイル群
    - 環境変数 PROJECT_DIR
- 主処理:
    1) vector_json 配下の .json ファイルを列挙
    2) 各 JSON を読み込み、配列は展開・単一オブジェクトはそのまま結合
    3) すべてのデータを 1 つの配列にまとめる
    4) merged_vector_json/vector.json として保存
- 出力:
    - PROJECT_DIR 配下の merged_vector_json/vector.json

補足:
- PROJECT_DIR が未設定の場合は RuntimeError で終了する。
- 入力フォルダが存在しない場合はエラー終了する。
"""

import os
import json
import pandas as pd
from pathlib import Path

from dotenv import load_dotenv  

# 環境変数を読み込む  
load_dotenv() 

PROJECT_DIR = os.getenv("PROJECT_DIR", "").strip()
if not PROJECT_DIR:
    raise RuntimeError("PROJECT_DIR is not set.")

def merge_vector_json_files(input_folder, output_file):
    """vector_jsonフォルダ内の全JSONファイルをマージする"""
    
    all_data = []
    processed_files = 0
    
    # vector_jsonフォルダ内の全JSONファイルを処理
    json_files = list(input_folder.glob("*.json"))
    
    for json_path in json_files:
        print(f"読み込み中: {json_path}")
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # データが配列形式かどうかをチェック
            if isinstance(data, list):
                all_data.extend(data)
            else:
                # 単一オブジェクトの場合はリストに追加
                all_data.append(data)
            
            processed_files += 1
            print(f"  -> {len(data) if isinstance(data, list) else 1} 件のデータを読み込み")
            
        except Exception as e:
            print(f"エラー: {json_path} の読み込み中にエラーが発生しました: {e}")
    
    # マージ結果を保存
    if all_data:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        print(f"\nマージ完了:")
        print(f"  処理ファイル数: {processed_files}")
        print(f"  総データ件数: {len(all_data)}")
        print(f"  出力ファイル: {output_file}")
    else:
        print("エラー: マージするデータが見つかりませんでした")

if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    IN_DIR = BASE_DIR / PROJECT_DIR / "vector_json"
    OUT_DIR = BASE_DIR / PROJECT_DIR / "merged_vector_json"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUT_DIR / "vector.json"

    # 入力フォルダの存在チェック
    if not IN_DIR.exists():
        print(f"エラー: {IN_DIR} フォルダが存在しません")
        exit(1)
    
    # vector_jsonフォルダ内の全JSONファイルをマージしてvector.jsonを作成
    merge_vector_json_files(IN_DIR, output_file)

