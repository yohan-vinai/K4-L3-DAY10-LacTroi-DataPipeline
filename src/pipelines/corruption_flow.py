from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Xay dung corruption -> evaluate -> repair -> compare flow."""
    print("=== BAT DAU CORRUPTION & REPAIR PIPELINE (CP4 & CP5) ===")
    settings = load_settings()

    # 1. Load baseline metrics & clean dataset
    print("[1/8] Loading baseline metrics va clean dataset...")
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    if settings.paths.clean_csv.exists():
        clean_df = pd.read_csv(settings.paths.clean_csv)
    else:
        records = fetch_source_records(settings)
        clean_df = build_clean_dataframe(records, now_utc())
        write_csv(clean_df, settings.paths.clean_csv)
        clean_df.to_json(settings.paths.clean_json, orient="records", indent=2)

    # 2. Tao corrupted dataframe
    print("[2/8] Tao synthetic corrupted dataframe...")
    corrupted_df = corrupt_clean_dataframe(clean_df, output_log_path=settings.paths.corruption_log)

    # 3. Save corrupted artifacts
    print(f"[3/8] Luu corrupted dataset vao {settings.paths.corrupted_clean_csv}...")
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    corrupted_df.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2)

    # 4. Rebuild index va evaluate tren corrupted data
    print("[4/8] Build Chroma index cho corrupted data va danh gia tren test set...")
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    print(
        f"      Corrupted Hit Rate: {corrupted_bundle.summary['retrieval_hit_rate']:.4f} | "
        f"Token F1: {corrupted_bundle.summary['mean_token_f1']:.4f} | "
        f"Judge Accuracy: {corrupted_bundle.summary['judge_accuracy']:.4f}"
    )

    # 5. Run quality checks & freshness SLA tren corrupted data
    print("[5/8] Kiem tra Data Observability (GX 1.x & Freshness SLA) tren corrupted data...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness_path = settings.paths.quality_dir / "corrupted_freshness_report.json"
    corrupted_freshness = build_freshness_report(corrupted_df, settings, corrupted_freshness_path)
    print(
        f"      Corrupted Quality Gate: {corrupted_quality['success']} | "
        f"Corrupted Freshness SLA: {corrupted_freshness['is_fresh']} "
        f"(stale ratio: {corrupted_freshness['stale_ratio']:.2%})"
    )

    # 6. Idempotent Repair: Clean lai tu raw records
    print("[6/8] Idempotent Repair: Chay lai cleaning pipeline tu raw records...")
    raw_records = fetch_source_records(settings)
    repaired_df = build_clean_dataframe(raw_records, now_utc())
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    repaired_df.to_json(settings.paths.repaired_clean_json, orient="records", indent=2)
    print(f"      Da repair {len(repaired_df)} dong du lieu.")

    # 7. Build index va evaluate tren repaired dataset
    print("[7/8] Build Chroma index cho repaired data va danh gia tren test set...")
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    print(
        f"      Repaired Hit Rate: {repaired_bundle.summary['retrieval_hit_rate']:.4f} | "
        f"Token F1: {repaired_bundle.summary['mean_token_f1']:.4f} | "
        f"Judge Accuracy: {repaired_bundle.summary['judge_accuracy']:.4f}"
    )

    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness_path = settings.paths.quality_dir / "repaired_freshness_report.json"
    repaired_freshness = build_freshness_report(repaired_df, settings, repaired_freshness_path)
    print(
        f"      Repaired Quality Gate: {repaired_quality['success']} | "
        f"Repaired Freshness SLA: {repaired_freshness['is_fresh']}"
    )

    # 8. Tao comparison report (3-state comparison)
    print(f"[8/8] Tao comparison report tai {settings.paths.comparison_report}...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print("=== CORRUPTION & REPAIR PIPELINE HOAN THANH XUAT SAC! ===")


if __name__ == "__main__":
    main()
