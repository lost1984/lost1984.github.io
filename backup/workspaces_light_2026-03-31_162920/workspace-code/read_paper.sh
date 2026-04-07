#!/usr/bin/env bash
set -euo pipefail

INPUT="${1:-}"
if [ -z "$INPUT" ]; then
  echo "用法: ./read_paper.sh <pdf_url|local_pdf> [length]" >&2
  exit 1
fi

LENGTH="${2:-medium}"
WORKDIR="${TMPDIR:-/tmp}/read_paper"
mkdir -p "$WORKDIR"
PDF_PATH=""
TXT_PATH=""

cleanup() {
  :
}
trap cleanup EXIT

if [[ "$INPUT" =~ ^https?:// ]]; then
  PDF_PATH="$WORKDIR/paper.pdf"
  echo "[1/3] 下载 PDF..." >&2
  curl -L --fail --silent --show-error "$INPUT" -o "$PDF_PATH"
else
  PDF_PATH="$INPUT"
fi

if [ ! -f "$PDF_PATH" ]; then
  echo "PDF 不存在: $PDF_PATH" >&2
  exit 1
fi

TXT_PATH="$WORKDIR/paper.txt"

echo "[2/3] 提取文本..." >&2
python3 - <<'PY' "$PDF_PATH" "$TXT_PATH"
import sys
from pathlib import Path
pdf_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])

text = ''
try:
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    chunks = []
    for page in reader.pages:
        try:
            chunks.append(page.extract_text() or '')
        except Exception:
            chunks.append('')
    text = '\n\n'.join(chunks)
except Exception:
    text = ''

if not text.strip():
    raise SystemExit('提取失败：需要先安装 pypdf。运行: python3 -m pip install --user pypdf')

out_path.write_text(text, encoding='utf-8')
print(out_path)
PY

if [ ! -s "$TXT_PATH" ]; then
  echo "文本提取失败" >&2
  exit 1
fi

echo "[3/3] 调用 summarize 总结..." >&2
export PATH="$HOME/.local/bin:$PATH"
summarize "$TXT_PATH" --length "$LENGTH"
