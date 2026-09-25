from __future__ import annotations

from pathlib import Path
import re
from statistics import mean
from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, read_json, write_json

DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s,;)\]`'\"]+", re.IGNORECASE)
NOT_FOUND_MARKERS = ("not found", "could not find", "no exact paper match", "has no", "don't know", "do not know")


def _normalize(text: str | None) -> str:
    return normalize_whitespace(text or "").lower()


def _is_correct(answer: str, ground_truth: str | None) -> bool:
    truth = _normalize(ground_truth)
    if not truth:
        return False
    answer_text = _normalize(answer)
    if truth in answer_text:
        return True
    truth_tokens = set(truth.split())
    return len(truth_tokens & set(answer_text.split())) / len(truth_tokens) >= 0.8


def _admits_missing(row: dict[str, Any]) -> bool:
    return bool(row.get("error")) or any(marker in _normalize(row.get("answer")) for marker in NOT_FOUND_MARKERS)


def _cited_ids(answer: str | None) -> list[str]:
    return sorted({match.rstrip(".").lower() for match in DOI_PATTERN.findall(answer or "")})


def _lookup_fell_back(row: dict[str, Any]) -> bool:
    names = [call["name"] for call in row.get("tool_calls", [])]
    return "lookup_paper" in names and "semantic_search_papers" in names[names.index("lookup_paper") + 1 :]


def _corruptions_by_paper(corruption_log: dict[str, Any] | None) -> dict[str, list[str]]:
    by_paper: dict[str, list[str]] = {}
    for change in (corruption_log or {}).get("corruptions", []):
        for paper_id in change.get("paper_ids", []):
            by_paper.setdefault(str(paper_id).lower(), []).append(change["type"])
    return by_paper


# One probe per corruption type, asking about the field that corruption damages.
PROBE_QUESTION_TYPES = {
    "drop_latest_records": "authors",
    "blank_summary": "summary",
    "inject_noise": "summary",
    "truncate_title": "summary",
    "stale_date": "date",
    "duplicate_rows": "authors",
}
PROBE_TEMPLATES = {
    "summary": "What is the summary of the paper '{title}'?",
    "authors": "Who authored '{title}'?",
    "date": "When was '{title}' published?",
    "categories": "What categories does '{title}' belong to?",
}


def build_probe_questions(clean_df: pd.DataFrame, corruption_log_path: Path) -> list[dict[str, Any]]:
    """Build agent-demo questions that target each corrupted paper type.

    The frozen benchmark may not touch every corruption (e.g. no blanked summary),
    so these probes guarantee the demo shows all six. Titles and ground truths come
    from the clean data, i.e. what a user would actually ask and expect.
    """
    clean_by_id = {str(row["paper_id"]).lower(): row for row in clean_df.to_dict(orient="records")}
    probes: list[dict[str, Any]] = []
    for change in read_json(corruption_log_path).get("corruptions", []):
        question_type = PROBE_QUESTION_TYPES.get(change["type"])
        paper_ids = sorted(str(paper_id).lower() for paper_id in change.get("paper_ids", []) if str(paper_id).lower() in clean_by_id)
        if not question_type or not paper_ids:
            continue
        paper = clean_by_id[paper_ids[0]]
        truths = {
            "summary": first_sentence(str(paper["summary"])),
            "authors": str(paper["authors_joined"]),
            "date": str(paper["published"]),
            "categories": str(paper["categories_joined"]),
        }
        probes.append(
            {
                "id": f"probe_{change['type']}",
                "question_type": question_type,
                "question": PROBE_TEMPLATES[question_type].format(title=paper["title"]),
                "ground_truth": truths[question_type],
                "ground_truth_doc_ids": [paper["paper_id"]],
                "corruption": change["type"],
            }
        )
    return probes


def diagnose_agent_answers(
    baseline_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    corruption_log_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Compare agent answers on a candidate collection against the baseline collection.

    A silent failure is an answer that is wrong, or cites the wrong paper, yet never
    admits missing data: the agent sounds confident while the corpus behind it is broken.
    """
    corruption_log = read_json(corruption_log_path) if corruption_log_path and corruption_log_path.exists() else None
    corruptions = _corruptions_by_paper(corruption_log)
    baseline_by_question = {row["question"]: row for row in baseline_rows}

    cases: list[dict[str, Any]] = []
    for row in candidate_rows:
        base = baseline_by_question.get(row["question"], {})
        target_ids = [str(paper_id).lower() for paper_id in (row.get("ground_truth_doc_ids") or [])]
        correct = _is_correct(row.get("answer", ""), row.get("ground_truth"))
        cited = _cited_ids(row.get("answer"))
        # Near-duplicate papers share authors and summaries, so a correct-looking answer
        # can still come from the wrong paper once the target is dropped or renamed.
        wrong_source = bool(cited) and bool(target_ids) and not set(cited) & set(target_ids)
        cases.append(
            {
                "id": row.get("id"),
                "question_type": row.get("question_type"),
                "question": row["question"],
                "ground_truth": row.get("ground_truth"),
                "baseline_answer": base.get("answer"),
                "answer": row.get("answer"),
                "baseline_correct": _is_correct(base.get("answer", ""), base.get("ground_truth")),
                "correct": correct,
                "cited_ids": cited,
                "wrong_source": wrong_source,
                "silent_failure": (not correct or wrong_source) and not _admits_missing(row),
                "lookup_fell_back_to_search": _lookup_fell_back(row),
                "top_doc_changed": base.get("top_search_doc_id") != row.get("top_search_doc_id"),
                "top_score_delta": round((row.get("top_search_score") or 0.0) - (base.get("top_search_score") or 0.0), 4),
                "target_corruptions": sorted({kind for paper_id in target_ids for kind in corruptions.get(paper_id, [])}),
            }
        )

    summary = {
        "baseline_collection": baseline_rows[0]["collection"] if baseline_rows else None,
        "candidate_collection": candidate_rows[0]["collection"] if candidate_rows else None,
        "questions": len(cases),
        "baseline_accuracy": mean(case["baseline_correct"] for case in cases) if cases else 0.0,
        "candidate_accuracy": mean(case["correct"] for case in cases) if cases else 0.0,
        "silent_failures": sum(case["silent_failure"] for case in cases),
        "wrong_source_answers": sum(case["wrong_source"] for case in cases),
        "admitted_missing": sum(not case["correct"] and not case["silent_failure"] for case in cases),
        "lookup_fallbacks": sum(case["lookup_fell_back_to_search"] for case in cases),
        "top_doc_changed": sum(case["top_doc_changed"] for case in cases),
    }
    report = {"summary": summary, "cases": cases}
    if output_path is not None:
        write_json(output_path, report)
    return report
