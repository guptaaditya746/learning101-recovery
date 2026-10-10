from pathlib import Path
import json
import re

PARSED_DIR = Path("parsed")
OUT_FILE = Path("data/chunks.jsonl")

CHUNK_SIZE = 1200
OVERLAP = 200


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP):
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = max(0, end - overlap)

    return chunks


def guess_section(chunk: str) -> str:
    lower = chunk.lower()

    if "abstract" in lower[:300]:
        return "abstract"
    if "introduction" in lower[:300]:
        return "introduction"
    if "related work" in lower[:300]:
        return "related_work"
    if "method" in lower[:300] or "approach" in lower[:300]:
        return "method"
    if "experiment" in lower[:300] or "evaluation" in lower[:300]:
        return "evaluation"
    if "conclusion" in lower[:300]:
        return "conclusion"

    return "unknown"


def main():
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    total = 0

    with OUT_FILE.open("w", encoding="utf-8") as f:
        for txt_path in sorted(PARSED_DIR.glob("*.txt")):
            paper_id = txt_path.stem
            text = clean_text(txt_path.read_text(encoding="utf-8", errors="ignore"))
            chunks = chunk_text(text)

            for i, chunk in enumerate(chunks):
                row = {
                    "paper_id": paper_id,
                    "chunk_id": f"{paper_id}_chunk_{i:04d}",
                    "section": guess_section(chunk),
                    "text": chunk,
                    "source_file": str(txt_path),
                    "char_start_approx": max(0, i * (CHUNK_SIZE - OVERLAP)),
                    "char_end_approx": max(0, i * (CHUNK_SIZE - OVERLAP)) + len(chunk),
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                total += 1

    print(f"Wrote {total} chunks to {OUT_FILE}")


if __name__ == "__main__":
    main()
