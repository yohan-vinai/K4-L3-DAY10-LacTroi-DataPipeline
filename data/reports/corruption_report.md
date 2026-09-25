# Corruption and Repair Comparison Report

## Quantitative Comparison: 3-State Overview

| Metric / Signal | Baseline (Clean) | Corrupted (Dirty) | Repaired (Recovered) |
|---|---:|---:|---:|
| samples | 10 | 10 | 10 |
| retrieval_hit_rate | 1.0000 | 0.5000 | 1.0000 |
| mean_token_f1 | 1.0000 | 0.6506 | 1.0000 |
| judge_accuracy | 1.0000 | 0.7000 | 1.0000 |
| mean_judge_score | 5 | 3.4000 | 5 |
| Quality Gate (GX 1.x) | True | False | True |
| Freshness SLA (is_fresh) | True | False | True |
| Stale Ratio | N/A | 0.2727 | 0.0417 |

## Quality Failures in Corrupted Data

- ❌ Violated Expectation: `expect_column_values_to_be_unique`
- ❌ Violated Expectation: `expect_column_value_lengths_to_be_between`

