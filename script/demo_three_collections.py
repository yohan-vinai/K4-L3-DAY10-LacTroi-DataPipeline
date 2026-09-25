"""Live demo: ask the same questions to papers-baseline, papers-corrupted and papers-repaired.

Run after `run_phase1.py` and `run_corruption_flow.py`:
    python script/demo_three_collections.py                  # one probe per corruption type
    python script/demo_three_collections.py "Who authored 'Some Paper Title'?"
"""

from __future__ import annotations

import sys

import pandas as pd

from core.config import load_settings
from retrieval.agent import build_agent, run_agent_question
from retrieval.diagnostics import build_probe_questions
from retrieval.index import LocalEmbeddingIndex

DEMO_CORRUPTIONS = ("truncate_title", "drop_latest_records", "stale_date", "blank_summary")


def main() -> None:
    settings = load_settings()
    manifests = {
        "baseline": settings.paths.embeddings_json,
        "corrupted": settings.paths.corrupted_embeddings_json,
        "repaired": settings.paths.repaired_embeddings_json,
    }
    missing = [str(path) for path in manifests.values() if not path.exists()]
    if missing:
        sys.exit(f"Missing index manifests {missing}. Run script/run_phase1.py and script/run_corruption_flow.py first.")

    if len(sys.argv) > 1:
        questions = [{"question": question} for question in sys.argv[1:]]
    else:
        clean_df = pd.read_json(settings.paths.clean_json, dtype={"published": str})
        probes = {probe["corruption"]: probe for probe in build_probe_questions(clean_df, settings.paths.corruption_log)}
        questions = [probes[name] for name in DEMO_CORRUPTIONS if name in probes]

    indexes = {name: LocalEmbeddingIndex.load(settings, path) for name, path in manifests.items()}
    agents = {name: build_agent(settings, index) for name, index in indexes.items()}
    print(f"LLM provider: {settings.llm_provider} | docs: " + ", ".join(f"{name}={index.collection.count()}" for name, index in indexes.items()))

    for item in questions:
        print("\n" + "=" * 100)
        if item.get("corruption"):
            print(f"[{item['corruption']}] expected: {item['ground_truth']}  (paper {item['ground_truth_doc_ids'][0]})")
        print(f"Q: {item['question']}")
        for name, index in indexes.items():
            top = index.search(item["question"], top_k=1)
            hit = f"{top[0].paper_id} score={top[0].score:.3f}" if top else "no hit"
            answer = run_agent_question(agents[name], item["question"])
            print(f"  {name:9s} | top-1 {hit} | {answer}")


if __name__ == "__main__":
    main()
