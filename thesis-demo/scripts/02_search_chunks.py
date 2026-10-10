from pathlib import Path
import json
import math
import re
import sys
from collections import Counter, defaultdict

CHUNKS_FILE = Path("data/chunks.jsonl")


def tokenize(text: str):
    return re.findall(r"[a-zA-Z0-9_\\-]+", text.lower())


def load_chunks():
    chunks = []
    with CHUNKS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            chunks.append(json.loads(line))
    return chunks


def build_bm25(chunks):
    tokenized = [tokenize(c["text"]) for c in chunks]
    doc_lens = [len(toks) for toks in tokenized]
    avgdl = sum(doc_lens) / max(1, len(doc_lens))

    df = defaultdict(int)
    for toks in tokenized:
        for term in set(toks):
            df[term] += 1

    return tokenized, doc_lens, avgdl, df


def bm25_score(query_terms, doc_terms, doc_len, avgdl, df, total_docs):
    k1 = 1.5
    b = 0.75
    counts = Counter(doc_terms)
    score = 0.0

    for term in query_terms:
        if term not in df:
            continue

        idf = math.log(1 + (total_docs - df[term] + 0.5) / (df[term] + 0.5))
        freq = counts[term]
        denom = freq + k1 * (1 - b + b * doc_len / avgdl)
        score += idf * ((freq * (k1 + 1)) / max(denom, 1e-9))

    return score


def main():
    if len(sys.argv) < 2:
        print('Usage: python scripts/02_search_chunks.py "your question"')
        raise SystemExit(1)

    query = " ".join(sys.argv[1:])
    chunks = load_chunks()
    tokenized, doc_lens, avgdl, df = build_bm25(chunks)

    query_terms = tokenize(query)
    scored = []

    for i, chunk in enumerate(chunks):
        score = bm25_score(
            query_terms=query_terms,
            doc_terms=tokenized[i],
            doc_len=doc_lens[i],
            avgdl=avgdl,
            df=df,
            total_docs=len(chunks),
        )
        scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)

    for rank, (score, chunk) in enumerate(scored[:5], start=1):
        print("=" * 80)
        print(f"Rank: {rank}")
        print(f"Score: {score:.4f}")
        print(f"Paper: {chunk['paper_id']}")
        print(f"Chunk: {chunk['chunk_id']}")
        print(f"Section: {chunk['section']}")
        print("-" * 80)
        print(chunk["text"][:1000].replace("\n", " "))
        print()


if __name__ == "__main__":
    main()
