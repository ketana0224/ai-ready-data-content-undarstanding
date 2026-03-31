"""
000_PDF_CUT.py の処理概要

- 入力: PROJECT_DIR 配下の pdf フォルダにある全ての PDF
- 主処理:
    1) 各 PDF を PyMuPDF (fitz) で開く
    2) 全ページを 1 ページずつ分割して新規 PDF を作成
    3) 連番付きファイル名で保存 (例: 元ファイル名_p01.pdf)
- 出力: PROJECT_DIR 配下の pdf_cut フォルダにページ単位 PDF を保存

補足:
- PROJECT_DIR を変更して処理対象フォルダを切り替える。
- 出力先フォルダが存在しない場合は自動作成する。
"""

from pathlib import Path
import os
import fitz  # PyMuPDF

from dotenv import load_dotenv  

# 環境変数を読み込む  
load_dotenv() 

# 環境
PROJECT_DIR = os.getenv("PROJECT_DIR", "").strip()
if not PROJECT_DIR:
    raise RuntimeError("PROJECT_DIR is not set.")

BASE_DIR = Path(__file__).resolve().parent
IN_DIR = BASE_DIR / PROJECT_DIR / "pdf"
OUT_DIR = BASE_DIR / PROJECT_DIR / "pdf_cut"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(IN_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in: {IN_DIR}")
        return

    print(f"Found {len(pdf_files)} PDF file(s) in: {IN_DIR}")

    processed_count = 0
    skipped_count = 0

    for in_pdf in pdf_files:
        try:
            with fitz.open(str(in_pdf)) as src:
                total = src.page_count
                pad = len(str(total))
                stem = in_pdf.stem

                for p in range(total):
                    out_path = OUT_DIR / f"{stem}_p{p+1:0{pad}d}.pdf"
                    with fitz.open() as dst:
                        # Some PDFs open fine in viewers but fail when grafting form/widget objects.
                        # Disable links/annots/widgets copy for robust page split.
                        dst.insert_pdf(src, from_page=p, to_page=p, links=0, annots=0, widgets=0)
                        dst.save(str(out_path))

            processed_count += 1
            print(f"Processed: {in_pdf.name} ({total} pages)")
        except Exception as ex:
            skipped_count += 1
            print(f"[Skip] Failed to process '{in_pdf.name}': {ex}")
            continue

    print(f"Done. processed={processed_count}, skipped={skipped_count}")


if __name__ == "__main__":
    main()