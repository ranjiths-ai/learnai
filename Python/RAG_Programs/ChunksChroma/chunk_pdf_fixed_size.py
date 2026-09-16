"""Create sequential fixed-size token chunks from a PDF.

The chunker intentionally ignores headings, subheadings, page boundaries, and
document structure. It writes only a chunk ID and the chunk text, with no
metadata and no overlap between chunks.

Usage:
    python chunk_pdf_fixed_size.py
    python chunk_pdf_fixed_size.py --input "chunking/HRPolicyDocument.pdf"
    python chunk_pdf_fixed_size.py --chunk-size 300 --output data/hr_policy_300_chunks.json

Install dependencies with:
    pip install pypdf tiktoken
"""

import argparse
import json
import re
import sys
from pathlib import Path


DEFAULT_INPUT = Path(__file__).parent / "chunking" / "HRPolicyDocument.pdf"
DEFAULT_OUTPUT = Path(__file__).parent / "data" / "hr_policy_300_chunks.json"
DEFAULT_CHUNK_SIZE = 300


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create non-overlapping fixed-size token chunks from a PDF."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to the source PDF.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path for the generated JSON file.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="Number of tokens per chunk (default: 300).",
    )
    return parser.parse_args()


def load_dependencies():
    try:
        from pypdf import PdfReader
        import tiktoken
    except ImportError as error:
        print(
            "Missing dependency. Install the PDF and tokenizer packages with:\n"
            "  pip install pypdf tiktoken",
            file=sys.stderr,
        )
        raise SystemExit(1) from error

    return PdfReader, tiktoken


def extract_pdf_text(input_path: Path, reader_type) -> str:
    reader = reader_type(str(input_path))
    page_text = [(page.extract_text() or "") for page in reader.pages]
    text = "\n".join(page_text)
    return re.sub(r"\s+", " ", text).strip()


def build_chunks(text: str, tokenizer, chunk_size: int) -> list[dict[str, str]]:
    token_ids = tokenizer.encode(text)
    chunks = []

    for start in range(0, len(token_ids), chunk_size):
        chunk_token_ids = token_ids[start:start + chunk_size]
        chunk_text = tokenizer.decode(chunk_token_ids).strip()
        if chunk_text:
            chunks.append(
                {
                    "chunk_id": f"chunk_{len(chunks) + 1:04d}",
                    "text": chunk_text,
                }
            )

    return chunks


def main() -> None:
    args = parse_args()

    if args.chunk_size <= 0:
        raise SystemExit("--chunk-size must be greater than zero.")
    if not args.input.is_file():
        raise SystemExit(f"Input PDF not found: {args.input}")

    pdf_reader, tiktoken = load_dependencies()
    tokenizer = tiktoken.get_encoding("cl100k_base")
    text = extract_pdf_text(args.input, pdf_reader)
    chunks = build_chunks(text, tokenizer, args.chunk_size)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as output_file:
        json.dump(chunks, output_file, indent=2, ensure_ascii=False)
        output_file.write("\n")

    token_count = len(tokenizer.encode(text))
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    print(f"Total tokens: {token_count}")
    print(f"Chunk size: {args.chunk_size}")
    print(f"Chunks written: {len(chunks)}")


if __name__ == "__main__":
    main()