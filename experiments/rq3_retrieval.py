"""
RQ3: Retrieval Recall@10 on AML query set (ADL graph vs plain baseline).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from data.aml.loader import ensure_dataset, index_all, load_queries
from experiments.baselines.plain_markdown import index_plain_markdown

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "aml"


def _tokenize(text: str) -> set[str]:
    return {w.lower() for w in text.split() if len(w) > 2}


def recall_at_k(
    mem_paths: list[Path],
    queries: list[dict],
    k: int = 10,
    use_relations: bool = True,
) -> float:
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "idx.db")
        if use_relations:
            mem = index_all(db)
        else:
            mem = index_plain_markdown(mem_paths, db)

        hits = 0
        total = len(queries)
        for q in queries:
            q_tokens = _tokenize(q["text"])
            relevant = set(q["relevant"])
            scored: list[tuple[str, float]] = []

            for entry in mem.hot.filter():
                doc = mem.retrieve(entry.adl_id)
                if not doc:
                    continue
                text = doc.markdown_body + " " + doc.concept_name
                doc_tokens = _tokenize(text)
                overlap = len(q_tokens & doc_tokens) / max(len(q_tokens), 1)
                if use_relations:
                    overlap += 0.1 * len(doc.relations)
                scored.append((entry.adl_id, overlap))

            scored.sort(key=lambda x: x[1], reverse=True)
            top_ids = {s[0] for s in scored[:k]}
            if relevant & top_ids:
                hits += 1

        mem.close()
        return hits / max(total, 1)


def run(k: int = 10) -> dict:
    ensure_dataset()
    paths = [DATA / e["path"] for e in json.loads((DATA / "manifest.json").read_text())["concepts"]]
    queries = load_queries()

    adl_recall = recall_at_k(paths, queries, k=k, use_relations=True)
    plain_recall = recall_at_k(paths, queries, k=k, use_relations=False)

    return {
        "metric": f"recall_at_{k}",
        "adl_recall": round(adl_recall, 4),
        "plain_baseline_recall": round(plain_recall, 4),
        "delta": round(adl_recall - plain_recall, 4),
        "n_queries": len(queries),
        "pilot": True,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
