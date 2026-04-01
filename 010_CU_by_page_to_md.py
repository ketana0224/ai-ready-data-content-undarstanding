"""
Azure Content Understanding Python SDK を使って PDF をページ単位で解析し、
Markdown を生成するサンプルスクリプト。

要件:
     - Python 3.9 以上

事前準備:
     - Microsoft Foundry リソースとモデルの構成は以下を参照:
        https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/contentunderstanding/azure-ai-contentunderstanding#configuring-microsoft-foundry-resource

設定:
     - 実行前に以下の環境変数を設定する。
        - AZURE_CONTENT_UNDERSTANDING_ENDPOINT: Content Understanding リソースのエンドポイント
        - AZURE_OPENAI_MODEL: 図版説明に使う Azure OpenAI モデル/デプロイ名
        - PROJECT_DIR: 入出力フォルダを含むプロジェクトディレクトリ名

使い方:
     1. このファイルがあるディレクトリへ移動する。
         cd path/to/the/directory/containing/this/file

     2. （任意）仮想環境を作成・有効化する。
         python -m venv .venv
         source .venv/bin/activate      # Linux/macOS
         .venv\\Scripts\\activate      # Windows

     3. 依存関係をインストールする。
         python -m pip install -r requirements.txt

     4. スクリプトを実行する。
         python 010_CU_by_page_to_md.py
"""

import sys
import json
import logging
import os
import re
import base64
from pathlib import Path

from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.ai.contentunderstanding.models import AnalysisInput, AnalysisResult
from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI
from dotenv import load_dotenv

from _common.polygon_cut import crop_image_from_file


def parse_source_to_page_bbox(source: str):
    """Parse CU source like D(1,x1,y1,...) into page index and bbox in inches."""
    if not source:
        return None

    nums = re.findall(r"[-+]?\d*\.?\d+", source)
    if len(nums) < 9:
        return None

    page_number = int(float(nums[0]))
    coords = [float(x) for x in nums[1:]]
    xs = coords[0::2]
    ys = coords[1::2]
    bbox = (min(xs), min(ys), max(xs), max(ys))
    return page_number - 1, bbox


def build_vision_client(credential: DefaultAzureCredential):
    endpoint = os.getenv("AZURE_OPENAI_API_ENDPOINT", "").strip()
    deployment = os.getenv("AZURE_OPENAI_MODEL", "").strip()
    if not endpoint:
        raise RuntimeError("AZURE_OPENAI_API_ENDPOINT is not set.")
    if not deployment:
        raise RuntimeError("AZURE_OPENAI_MODEL is not set.")

    token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")
    client = OpenAI(base_url=endpoint, api_key=token_provider())
    return client, deployment


def describe_figure(client: OpenAI, model: str, image_path: Path) -> str:
    vision_prompt = """画像を出来る限り詳しく分かりやすく説明してください。
ロゴと考えられる場合は会社名や組織を推測して、その名前と「ロゴ」とのみ出力してください。
この図版の内容を日本語で5文から10文以内で要約してください。数値や軸、凡例、主メッセージを優先してください。
この図版が何らかのプロセスやフローを表している場合は、そのプロセスの内容を説明してください。また加えてmermaid記法でフロー図を出力してください。
この図版が何らかのチャートを表している場合は、そのチャートの内容を説明してください。また加えてHTML記法で表を出力してください。"""


    img_b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": vision_prompt,
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                    },
                ],
            }
        ],
    )
    return (resp.choices[0].message.content or "").strip()


def enrich_markdown_with_figure_descriptions(result_dict: dict, target_pdf: Path, out_dir: Path, credential: DefaultAzureCredential):
    contents = result_dict.get("contents", [])
    if not contents:
        return "", []

    markdown = contents[0].get("markdown", "")
    figures = contents[0].get("figures", [])
    if not figures:
        return markdown, []

    figure_dir = out_dir.parent / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    vision_client, vision_model = build_vision_client(credential)
    descriptions = []

    for figure in figures:
        figure_id = figure.get("id")
        source = figure.get("source", "")
        parsed = parse_source_to_page_bbox(source)
        if not figure_id or not parsed:
            continue

        page_idx, bbox = parsed
        img = crop_image_from_file(str(target_pdf), page_idx, bbox)
        img_path = figure_dir / f"{target_pdf.stem}_{figure_id}.png"
        img.save(img_path)

        description = describe_figure(vision_client, vision_model, img_path)
        descriptions.append((figure_id, str(img_path), description))

        ref = f"figures/{figure_id}"
        marker = f"]({ref})"
        addition = f"]({ref})\n\n> Figure {figure_id} description: {description}"
        if marker in markdown:
            markdown = markdown.replace(marker, addition, 1)
        else:
            markdown += f"\n\n> Figure {figure_id} description: {description}"

    return markdown, descriptions


def main() -> None:
    load_dotenv()
    project_dir = os.getenv("PROJECT_DIR", "").strip()
    if not project_dir:
        raise RuntimeError("PROJECT_DIR is not set.")

    # Insert the following configurations.
    # 1) MICROSOFT_FOUNDRY_ENDPOINT - the endpoint to your Content Understanding resource.
    endpoint = os.getenv("MICROSOFT_FOUNDRY_ENDPOINT", "").strip()
    if not endpoint:
        raise RuntimeError("MICROSOFT_FOUNDRY_ENDPOINT is not set.")

    # 3) Local PDF files to analyze
    base_dir = Path(__file__).resolve().parent
    pdf_dir = base_dir / project_dir / "pdf_cut"
    if not pdf_dir.exists():
        print(f"[Error] PDF folder not found: {pdf_dir}")
        sys.exit(1)

    target_pdfs = sorted(pdf_dir.glob("*.pdf"))
    if not target_pdfs:
        print(f"[Error] No PDF files found in: {pdf_dir}")
        sys.exit(1)

    # ANALYZER_ID - the ID of the analyzer to use.
    analyzer_id = "prebuilt-layout"

    # API_VERSION - the API version to use.
    api_version = "2025-11-01"

    # Set up Content Understanding client with Entra ID authentication.
    credential = DefaultAzureCredential()
    client = ContentUnderstandingClient(endpoint=endpoint, credential=credential, api_version=api_version)

    out_dir = base_dir / project_dir / "cu_md"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ログファイルの設定
    log_file = base_dir / project_dir / "010_error.log"
    logging.basicConfig(
        filename=str(log_file),
        level=logging.ERROR,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
    )

    print(f"Found {len(target_pdfs)} PDF files in: {pdf_dir}")

    for idx, target_pdf in enumerate(target_pdfs, start=1):
        print("=" * 80)
        print(f"[{idx}/{len(target_pdfs)}] Analyzing with {analyzer_id} analyzer...")
        print(f"  File Path: {target_pdf}\n")

        out_md = out_dir / f"{target_pdf.stem}.md"
        if out_md.exists():
            print(f"[Skip] Output markdown already exists: {out_md}")
            continue

        file_bytes = target_pdf.read_bytes()

        try:
            poller = client.begin_analyze(
                analyzer_id=analyzer_id,
                inputs=[
                    AnalysisInput(
                        name=target_pdf.name,
                        data=file_bytes,
                        mime_type="application/pdf",
                    )
                ],
            )
            result: AnalysisResult = poller.result()
        except AzureError as err:
            msg = f"[Azure Error] {target_pdf.name}: {err.message}"
            print(msg)
            logging.error(msg)
            continue
        except Exception as ex:
            msg = f"[Unexpected Error] {target_pdf.name}: {ex}"
            print(msg)
            logging.error(msg)
            continue

        result_dict = result.as_dict()

        try:
            enriched_markdown, figure_details = enrich_markdown_with_figure_descriptions(
                result_dict=result_dict,
                target_pdf=target_pdf,
                out_dir=out_dir,
                credential=credential,
            )
        except Exception as ex:
            msg = f"[Figure Description Error] {target_pdf.name}: {ex}"
            print(msg)
            logging.error(msg)
            enriched_markdown = ""
            figure_details = []

        if enriched_markdown:
            out_md.write_text(enriched_markdown, encoding="utf-8")
            print(f"Wrote enriched markdown: {out_md}")

        if figure_details:
            print("Figure descriptions generated:")
            for fig_id, img_path, _ in figure_details:
                print(f"  - {fig_id}: {img_path}")

        # [START output_result]
        print("=" * 50)
        print(f"Analysis result ({target_pdf.name}):")
        print("=" * 50 + "\n")

        max_display_lines = 50
        result_str = json.dumps(result_dict, indent=2)
        ret_lines = result_str.splitlines()

        if len(ret_lines) > max_display_lines:
            print("\n".join(ret_lines[:max_display_lines]))
            print(f"\n {len(ret_lines) - max_display_lines} more lines to be displayed...\n")
        else:
            print(result_str)
        # [END output_result]


if __name__ == "__main__":
    main()