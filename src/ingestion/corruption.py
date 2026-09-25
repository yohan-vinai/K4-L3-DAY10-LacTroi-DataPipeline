from __future__ import annotations

import pandas as pd
from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """TODO(student): simulate nhieu dang data corruption.

    Pseudo-code:
    1. Drop mot so latest records.
    2. Blank summary o mot so dong.
    3. Inject noise vao text.
    4. Lam title bi truncate.
    5. Lam published date cu di.
    6. Add duplicate rows.
    7. Rebuild `text_for_embedding`.
    8. Ghi corruption log vao output_log_path.
    """
    corrupted = df.copy(deep=True)
    log: list[dict] = []

    def record(scenario, ids, details):
        log.append({"scenario": scenario, "paper_ids": [str(x) for x in ids], "details": details})

    # Stable selection makes the corruption experiment reproducible.
    ordered = corrupted.sort_values(["published", "paper_id"], ascending=[False, True])
    drop_n = max(1, int(round(len(corrupted) * 0.20)))
    drop_ids = ordered.head(drop_n)["paper_id"].tolist()
    corrupted = corrupted[~corrupted.paper_id.isin(drop_ids)].copy()
    record("drop_latest_records", drop_ids, {"fraction": 0.20, "count": len(drop_ids)})

    remaining = corrupted.sort_values("paper_id", kind="mergesort")
    blank_ids = remaining.head(max(1, int(round(len(remaining) * 0.20))))["paper_id"].tolist()
    corrupted.loc[corrupted.paper_id.isin(blank_ids), "summary"] = ""
    record("blank_summary", blank_ids, {"fraction": 0.20})

    noise_ids = remaining.iloc[-min(2, len(remaining)):]["paper_id"].tolist()
    corrupted.loc[corrupted.paper_id.isin(noise_ids), "summary"] = corrupted.loc[
        corrupted.paper_id.isin(noise_ids), "summary"
    ].map(lambda value: f"{value} [NOISE_TAG_ERR_404_DATA_CORRUPTED]")
    record("inject_noise", noise_ids, {"tag": "NOISE_TAG_ERR_404_DATA_CORRUPTED"})

    title_ids = remaining.iloc[1:1 + min(2, max(0, len(remaining) - 1))]["paper_id"].tolist()
    corrupted.loc[corrupted.paper_id.isin(title_ids), "title"] = corrupted.loc[
        corrupted.paper_id.isin(title_ids), "title"
    ].map(lambda value: str(value)[:6])
    record("truncate_title", title_ids, {"max_characters": 6})

    # Make the freshness SLA visibly fail (>25% of the post-drop corpus).
    stale_count = max(6, int(len(remaining) * 0.30))
    stale_ids = remaining.iloc[-min(stale_count, len(remaining)):]["paper_id"].tolist()
    corrupted.loc[corrupted.paper_id.isin(stale_ids), "published"] = "2020-01-01"
    corrupted.loc[corrupted.paper_id.isin(stale_ids), "age_days"] = 365 * 3
    record("stale_date", stale_ids, {"published": "2020-01-01"})

    duplicate_ids = remaining.iloc[:min(2, len(remaining))]["paper_id"].tolist()
    duplicates = corrupted[corrupted.paper_id.isin(duplicate_ids)].copy()
    corrupted = pd.concat([corrupted, duplicates], ignore_index=True)
    record("duplicate_rows", duplicate_ids, {"count": len(duplicate_ids)})

    corrupted["summary_chars"] = corrupted["summary"].fillna("").astype(str).str.len()
    corrupted["text_for_embedding"] = corrupted.apply(
        lambda row: f"Title: {row['title']}\nAuthors: {row['authors_joined']}\n"
        f"Published: {row['published']}\nCategories: {row['categories_joined']}\n"
        f"Summary: {row['summary']}", axis=1
    )
    write_json(output_log_path, {"scenarios": log, "total_scenarios": len(log), "rows_after_corruption": len(corrupted)})
    return corrupted.reset_index(drop=True)
