from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex
import pandas as pd

def main() -> None:
    """TODO(student): xay dung corruption -> evaluate -> repair -> compare flow.

    Pseudo-code:
    1. Load baseline metrics va clean dataset.
    2. Tao corrupted dataframe.
    3. Save corrupted artifacts.
    4. Rebuild index va evaluate.
    5. Run quality checks/freshness tren corrupted data.
    6. Repair lai tu raw records.
    7. Evaluate repaired dataset.
    8. Tao comparison report.
    """
    settings = load_settings()
    clean_df = pd.read_csv(settings.paths.clean_csv)
    baseline_metrics = read_json(settings.paths.baseline_metrics)

    # CP4: corrupt, persist, quality-check, index and evaluate.
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    corrupted_df.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2)
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, settings.paths.corrupted_embeddings_json)
    corrupted_bundle = evaluate_pipeline(settings, corrupted_index, settings.paths.eval_testset,
                                         settings.paths.corrupted_metrics, settings.paths.corrupted_answers)
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, settings.paths.quality_dir / "corrupted_freshness_report.json"
    )

    # CP5: repair from immutable raw records, never from the corrupted frame.
    repaired_df = build_clean_dataframe(load_raw_records(settings.paths.raw_records_json), now_utc())
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    repaired_df.to_json(settings.paths.repaired_clean_json, orient="records", indent=2)
    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.repaired_embeddings_json)
    repaired_bundle = evaluate_pipeline(settings, repaired_index, settings.paths.eval_testset,
                                        settings.paths.repaired_metrics, settings.paths.repaired_answers)
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, settings.paths.quality_dir / "repaired_freshness_report.json"
    )
    generate_corruption_report(
        settings.paths.comparison_report, baseline_metrics, corrupted_bundle.summary,
        repaired_bundle.summary, corrupted_quality, repaired_quality,
        corrupted_freshness, repaired_freshness,
    )
    print(f"CP4 corrupted: hit_rate={corrupted_bundle.summary['retrieval_hit_rate']:.4f}, "
          f"quality={corrupted_quality['success']}, freshness={corrupted_freshness['is_fresh']}")
    print(f"CP5 repaired: hit_rate={repaired_bundle.summary['retrieval_hit_rate']:.4f}, "
          f"quality={repaired_quality['success']}, freshness={repaired_freshness['is_fresh']}")
