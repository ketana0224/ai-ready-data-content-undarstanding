"""
【仕様説明】035_json_orverlap.py

■ 目的
  vector_json フォルダ内のページ別JSONファイルに対して、
  同じ file_name を持つ「1つ先のページ」の content を
  自身の content の末尾に追記する（オーバーラップ処理）。

■ 処理フロー
  1. IN_DIR (vector_json/) 内の全 .json ファイルを順に処理する。
  2. 各レコードの file_name と page を読み取り、
     次ページのJSONファイル（{file_name}_p{page+1}.json）を検索する。
  3. 次ページが存在する場合、その content を現在の content の末尾に改行で連結する。
  4. 次ページが存在しない場合（最終ページ）は content をそのまま保持する。
  5. 処理結果を OUT_DIR (overlap_json/) に同名ファイルとして出力する。

■ 入出力
  入力 : {PROJECT_DIR}/vector_json/*.json
  出力 : {PROJECT_DIR}/overlap_json/*.json  （同名ファイル）

■ スキップ条件
  出力先に同名ファイルが既に存在する場合は処理をスキップする。

■ 備考
  - page フィールドはゼロ埋め文字列（例: "01", "002"）を想定。
  - 1つのページJSONに複数レコードが存在する場合、
    次ページの全レコードの content を結合して追記する。
"""

import os
import json
from pathlib import Path

from dotenv import load_dotenv  

# 環境変数を読み込む  
load_dotenv() 

PROJECT_DIR = os.getenv("PROJECT_DIR", "").strip()
if not PROJECT_DIR:
    raise RuntimeError("PROJECT_DIR is not set.")


def get_next_page_content(in_dir: Path, file_name: str, page, json_path: Path) -> str | None:
    """同じfile_nameの次ページのcontentを取得する。次ページが存在しない場合はNoneを返す。"""
    next_page_num = int(page) + 1
    # ゼロ埋め桁数をファイル名の "_p数字" 部分から取得する
    stem = json_path.stem  # 例: GRORY-IR-2024-RSaj_p01
    p_part = stem.rsplit("_p", 1)[-1]  # 例: "01"
    pad_len = len(p_part)
    next_page_str = str(next_page_num).zfill(pad_len)
    next_json_path = in_dir / f"{file_name}_p{next_page_str}.json"

    if not next_json_path.exists():
        return None

    with open(next_json_path, "r", encoding="utf-8") as f:
        next_data = json.load(f)

    contents = [r.get("content", "") for r in next_data if r.get("content", "")]
    return "\n".join(contents) if contents else None


def process_json_file(json_path: Path, in_dir: Path, output_path: Path):
    """単一のJSONファイルを処理して次ページのcontentをオーバーラップとして追加"""
    print(f"処理中: {json_path}")

    if output_path.exists():
        print(f"スキップ: {output_path} は既に存在します")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for record in data:
        file_name = record.get("file_name", "")
        page = record.get("page", "")

        if file_name and page is not None:
            next_content = get_next_page_content(in_dir, file_name, page, json_path)
            if next_content:
                record["content"] = record.get("content", "") + "\n" + next_content
                print(f"  次ページ({int(page)+1})のcontentを追加しました")
            else:
                print(f"  次ページなし（最終ページ）")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    print(f"オーバーラップJSONファイル出力: {output_path}")

if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    IN_DIR = BASE_DIR / PROJECT_DIR / "vector_json"
    OUT_DIR = BASE_DIR / PROJECT_DIR / "overlap_json"
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
                process_json_file(IN_JSON, IN_DIR, output_path)
            except Exception as e:
                print(f"エラー: {IN_JSON} の処理中にエラーが発生しました: {e}")

            # break  # テスト用に最初の1ファイルのみ処理
        
        print(f"\nCompleted processing {len(json_files)} JSON file(s)")

