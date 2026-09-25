# Group Report — Day 10: Data Pipeline & Data Observability

> Báo cáo nhóm K4-L3A-DAY10, cập nhật theo artifacts hiện có trong repository.

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4-L3A |
| Tên nhóm         | Lạc Trôi |
| Repository         | https://github.com/yohan-vinai/K4-L3-DAY10-LacTroi-DataPipeline |
| Ngày hoàn thành | 2026-09-25 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Trần Phạm Thái Vũ | 2A202602695 | Trưởng nhóm / Pipeline Integrator | `src/core/`, `src/pipelines/`, `script/` |
| 2 | Võ Phú Hãn | 2A202602628 | Data Core Lead | `src/ingestion/`, raw và clean data |
| 3 | Nguyễn Tiến Tuân | 2A202602595 | RAG & Vector Index | `src/retrieval/`, ChromaDB |
| 4 | Vũ Duy Điệp | 2A202602703 | Observability & Evaluation | `src/observability/`, `src/evaluation/` |

## 2. Tóm tắt kết quả

**Tóm tắt của nhóm:**

Nhóm đã hoàn thành CP0–CP5: ingestion từ raw snapshot, cleaning, benchmark RAG 10 câu, baseline, corruption, repair và báo cáo đối chiếu. Artifacts baseline ghi nhận 24 bài báo, Retrieval Hit Rate 1.0000, Mean Token F1 1.0000, Judge Accuracy 1.0000, Judge Score 5.0; 6 expectation và Freshness SLA đều pass. Corruption seed 42 loại 5 bài mới nhất, làm rỗng summary ở 4 dòng, thêm noise vào 3 dòng, rút title ở 3 dòng, làm stale 6 dòng và nhân bản 3 dòng; dataset còn 22 dòng. Quality Gate phát hiện duplicate `paper_id` và summary quá ngắn; freshness báo stale ratio 27.27%. Trên cùng test set, hit rate còn 0.5000, Token F1 còn 0.6506 và Judge Score còn 3.4. Answer artifacts ghi judge dùng fallback heuristic vì LLM evaluator không khả dụng; các điểm này không phải kết quả LLM Judge trực tiếp. Repair tạo lại 24 dòng từ raw snapshot, quality/freshness pass và metrics trở lại baseline. Commit kiểm thử `0c809ab` ghi nhận hai pipeline exit 0; artifacts được tạo lúc 2026-09-25 10:51 UTC. CP6 còn các bước demo/Q&A, xác nhận contributor và nộp LMS. Tập dữ liệu nhỏ và test set 10 câu là giới hạn chính.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records
    -> cleaning và data modeling
    -> embedding + ChromaDB index
    -> evaluation baseline
    -> quality/freshness reports
    -> corruption
    -> re-index và re-evaluate
    -> repair từ dữ liệu nguồn
    -> comparison report
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
|---|---|---|---|---|
| Ingestion | Crossref API hoặc raw snapshot | Fetch có timeout/retry và offline fallback | `data/raw/crossref_response.json`, `crossref_records.json` | Võ Phú Hãn |
| Cleaning | Raw records | Chuẩn hóa schema, `age_days`, `text_for_embedding` | `data/clean/papers_clean.csv`, `.json` | Võ Phú Hãn |
| Embedding/index | Clean DataFrame | MiniLM-L6-v2 và ChromaDB collections | `data/chroma/`, `data/embeddings/` (runtime) | Nguyễn Tiến Tuân |
| Evaluation | Test set và vector index | Hit rate, Token F1, judge metrics | `data/results/*_metrics.json` | Nguyễn Tiến Tuân, Vũ Duy Điệp |
| Observability | DataFrame theo từng trạng thái | GX 1.x checks và freshness SLA | `data/quality/*_report.json` | Vũ Duy Điệp |
| Corruption/repair | Clean data và raw snapshot | 6 lỗi tổng hợp, repair bằng cách rebuild từ raw | `data/results/corruption_log.json`, repaired dataset (runtime) | Võ Phú Hãn, Trần Phạm Thái Vũ |
| Orchestration | Settings và các module trên | Baseline và corruption flow | `src/pipelines/`, `script/` | Trần Phạm Thái Vũ |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER` | `gemini` mặc định cấu hình; artifacts chỉ xác nhận judge metrics, không xác nhận provider runtime |
| `LLM_MODEL` | `gemini-2.5-flash` mặc định |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 trong snapshot đã lưu |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày; stale ratio giới hạn 25% |
| Random seed | 42 |

Không dán nội dung API key hoặc file `.env` vào báo cáo.

### Lệnh cài đặt

```bash
uv sync
```

### Lệnh chạy

Baseline:

```bash
uv run python script/run_phase1.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
uv run python script/run_corruption_flow.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Nhóm đã chạy `run_phase1.py` thành công, exit 0 | Artifacts sinh lúc 2026-09-25 10:51 UTC | Commit kiểm thử `0c809ab`, `phase1_report.md`, baseline metrics/quality/freshness JSON |
| Corruption flow | Nhóm đã chạy `run_corruption_flow.py` thành công, exit 0 | Artifacts sinh lúc 2026-09-25 10:51 UTC | Commit kiểm thử `0c809ab`, corrupted/repaired metrics, quality/freshness, corruption log; 24 → 22 → 24 dòng |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source | Crossref REST API (`https://api.crossref.org/works`) |
| Query/filter | `agentic retrieval augmented generation large language model`; `has-abstract:true`; filter date configured dynamically |
| Thời điểm lấy dữ liệu | Raw artifacts hiện có; không khẳng định lần fetch live gần nhất |
| Số record nhận được | 24 trong snapshot |
| Cơ chế retry/backoff | Timeout 20s, exponential backoff 1/2/4s, fallback raw snapshot |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | String | Có | DOI định danh | Bỏ record nếu thiếu |
| `title`, `summary` | String | Có | Tiêu đề và abstract | Chuẩn hóa/strip; bỏ record thiếu field thiết yếu |
| `published` | ISO date string | Có | Ngày xuất bản | Lấy từ metadata Crossref, chuẩn hóa ngày |
| `authors_joined`, `categories_joined` | String | Không | Tác giả/chủ đề phân cách `, ` | Để trống khi không có |
| `abs_url`, `pdf_url` | String | Không | Liên kết nguồn | DOI URL và PDF link nếu có |
| `age_days` | Integer | Có | Tuổi bài báo theo ngày | Tính từ ngày chạy và `published` |
| `text_for_embedding` | String | Có | Năm dòng title/authors/published/categories/summary | Tạo sau cleaning và cập nhật sau corruption |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Bỏ record thiếu DOI hoặc title | Completeness/Validity | Không ghi số lượng riêng trong artifact | `src/ingestion/cleaning.py` |
| Chuẩn hóa abstract, whitespace, ngày, tác giả/chủ đề và embedding text | Validity/Consistency | 24 dòng clean | `data/clean/papers_clean.json` schema và `phase1_report.md` |
| Deduplicate theo `paper_id` | Uniqueness | 0 raw duplicates theo report; 3 duplicate được inject | clean dataset và corruption log |

Giải thích cách nhóm tạo `text_for_embedding`, document ID và `age_days`:

`paper_id` lấy từ DOI. `age_days` là chênh lệch ngày giữa thời điểm chạy và `published`. `text_for_embedding` ghép 5 nhãn Title, Authors, Published, Categories, Summary thành năm dòng; corruption rebuild chuỗi sau khi đổi title/summary.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi | 10 |
| Các `question_type` | summary, authors, date, categories |
| Ground-truth document ID | DOI trong `data/eval/test_set.json` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection | ChromaDB; papers-baseline/corrupted/repaired |
| Retrieval `top_k` | 4 |
| Judge | Answer artifacts ghi fallback heuristic; LLM evaluator unavailable ở lần chạy được lưu |
| LLM provider/model | Settings mặc định Gemini 2.5 Flash; runtime provider chưa xác nhận từ metrics JSON |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` |

Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:

Giữ nguyên câu hỏi và ground truth để biến dữ liệu/index thành biến thay đổi chính. Nhờ đó, chênh lệch giữa ba trạng thái có thể so sánh trực tiếp trên cùng 10 câu hỏi.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records | `data/raw/` | Có | Snapshot 24 records |
| Cleaned dataset | `data/clean/papers_clean.csv`, `.json` | Có | 24 records |
| Embedding manifest/index | `data/chroma/`, `data/embeddings/` | Có | 3 collections baseline/corrupted/repaired; manifests có trong repo |
| Evaluation set | `data/eval/test_set.json` | Có | 10 câu |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Hit rate/F1/judge accuracy 1.0 |
| Quality/freshness | `data/quality/` | Có | 6/6 pass; freshness true |
| Baseline report | `data/reports/phase1_report.md` | Có | Report tự sinh |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` | 1.0000 | Ground truth retrieved for 10/10 questions |
| `mean_token_f1` | 1.0000 | Mean token overlap score |
| `judge_accuracy` | 1.0000 | 10/10 judged materially correct |
| `mean_judge_score` | 5.0000 | Mean fallback heuristic judge score on 1–5 scale; not an LLM judge run |
| Ragas | Skipped | Not run; artifact records opt-in `RUN_RAGAS=1` |

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
|---|---|---|---|---|
| Row count | Completeness | 5–5000 rows | Pass, 24 rows | `baseline_quality_report.json` |
| `paper_id` non-null and unique | Completeness/Uniqueness | 0 null, 100% unique | Pass, 24/24 unique | `baseline_quality_report.json` |
| `title`, `text_for_embedding` non-null | Completeness | 0 null | Pass | `baseline_quality_report.json` |
| `summary` minimum length | Validity | >= 30 chars | Pass | `baseline_quality_report.json` |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Clean dataset (`data/quality/freshness_report.json`) |
| Timestamp mới nhất | 2026-07-22 |
| Ngưỡng freshness | 180 ngày; stale ratio tối đa 25% |
| Trạng thái baseline | Fresh (`is_fresh=true`) |
| Lý do | 1/24 stale, ratio 4.17% |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| Drop latest records | Bỏ 20% mới nhất theo `published` | 5 | Retrieval hụt tài liệu mới | Corruption log; hit rate 0.50 | Rebuild từ raw snapshot |
| Blank summary | Để trống 20% summary còn lại | 4 | Summary length check fail | GX báo 4 unexpected | Rebuild từ raw |
| Inject noise | Thêm marker rác vào summary | 3 | Embedding text nhiễu | Corruption log và F1 giảm tổng thể | Rebuild từ raw |
| Truncate title | Rút title xuống 5 ký tự | 3 | Title mất thông tin | Corruption log | Rebuild từ raw |
| Stale date | Đặt published về 365 ngày trước | 6 | Freshness fail | 6/22 stale, 27.27% | Dùng ngày trong raw |
| Duplicate rows | Thêm bản sao của 3 dòng | 3 bản sao | Unique ID check fail | 6 unexpected duplicate values trong GX | Deduplicate/rebuild từ raw |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Đã có trong repository tại `data/results/corruption_log.json`.
- Nhận xét: Log lưu seed 42, 24 dòng đầu, 22 dòng cuối, đủ 6 loại lỗi, paper IDs bị tác động, ngày stale và số dòng theo từng lỗi.

Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:

Luồng repair đọc lại raw records rồi gọi `build_clean_dataframe`, không vá trên corrupted DataFrame. Artifact repaired có 24 rows, Quality Gate 6/6 pass, Freshness `is_fresh=true`, và metrics trở về baseline. Raw snapshot là nguồn phục hồi được lưu trong repository.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
|---|---:|---:|---:|---:|---:|---|
| `retrieval_hit_rate` | 1.0000 | 0.5000 | 1.0000 | 🔻 Giảm 50.00% | 100% | Mất 5 bài báo mới khiến 5 câu hỏi truy vấn trượt hoàn toàn; phục hồi hoàn toàn sau repair |
| `mean_token_f1` | 1.0000 | 0.6506 | 1.0000 | 🔻 Giảm 34.94% | 100% | Abstract rỗng và chuỗi rác làm câu trả lời thiếu hụt thông tin; phục hồi 100% |
| `judge_accuracy` | 1.0000 | 0.7000 | 1.0000 | 🔻 Giảm 30.00% | 100% | 3 câu hỏi trượt hoàn toàn nội dung; phục hồi chuẩn xác sau repair |
| `mean_judge_score` | 5.0000 | 3.4000 | 5.0000 | 🔻 Giảm 1.60 điểm | 100% | Điểm chất lượng sụt giảm nghiêm trọng; trở lại điểm tối đa 5/5 |
| Quality Gate (GX 1.x) | True | False | True | ❌ Bị đánh trượt | 100% | Bắt lỗi duplicate ID và empty summary; vượt qua sau repair |
| Freshness SLA (is_fresh) | True | False | True | ❌ Bị cảnh báo | 100% | Stale ratio từ 27.27% giảm về 4.17% sau repair |

**Kết luận dựa trên artifacts:**
1. Corruption trùng với 2 expectation thất bại, Freshness SLA `False` (6/22 stale), retrieval hit rate 0.5000 và Token F1 0.6506 trên cùng benchmark.
2. Repair từ raw snapshot tái tạo 24 dòng; 6/6 expectation và freshness đều pass, các metric phục hồi về giá trị baseline.
Các kết quả thể hiện mối liên hệ trong lần chạy ghi nhận: corruption đi cùng các quality/freshness alert và suy giảm metric; rebuild từ raw snapshot đi cùng việc quality/freshness và metric phục hồi. Các artifact không cô lập tác động của từng loại corruption riêng lẻ.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Great Expectations datasource API cũ gây lỗi khi chạy với GX 1.x.
- **Nguyên nhân:** API Fluent Datasource thay đổi ở GX 1.x.
- **Cách xử lý:** Dùng ephemeral context và pandas datasource API trong `src/observability/quality.py`.
- **Cách xác minh:** baseline/repaired quality artifacts đạt 6/6; corrupted đạt 4/6 và ghi nhận hai expectation fail.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Tập dữ liệu chỉ có 24 bài báo | Chưa đại diện tải lớn hoặc nhiều lĩnh vực | Chạy benchmark với tập lớn hơn và ghi rõ snapshot/query |
| Benchmark có 10 câu hỏi, Ragas chưa chạy | Độ bao phủ tình huống hỏi còn hạn chế | Mở rộng test set và chạy `RUN_RAGAS=1` khi môi trường cho phép |
| Lần chạy được lưu dùng fallback heuristic judge; model embedding cần tải từ Hugging Face trên máy chưa có cache | Điểm judge chưa phải đánh giá LLM độc lập và clean setup không chạy offline được | Chạy lại với LLM key/provider và cache model có sẵn; ghi provider thực tế vào artifacts |
| Repository chưa có pytest suite/CI | Chưa có automated regression gate cho mọi module | Thêm tests cho ingestion, cleaning, corruption, quality và retrieval, sau đó chạy trong CI |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm/repository theo `docs/TEAM.md` và remote metadata.
- [x] Phân công khớp module/artifact; MSSV còn thiếu để N/A.
- [x] CP0–CP5: raw snapshot, clean data, test set, 3 Chroma collections, baseline/corrupted/repaired metrics, quality/freshness reports, corruption log và comparison report đều có trong repo; commit `0c809ab` ghi nhận cả hai pipeline exit 0.
- [x] PR #12 đã merge; commit report cuối đã được đẩy lên remote `main`.
- [x] GitHub Contributors API liệt kê tài khoản của cả bốn thành viên: `yohan-vinai`, `elysszxje`, `t00-tuannguyen`, `VuDuyDiepAI`.
- [x] Ba trạng thái dùng cùng `data/eval/test_set.json`.
- [x] Metrics và quality/freshness khớp JSON artifacts đã lưu.
- [x] Đường dẫn báo cáo và artifacts được đối chiếu trong working tree.
- [x] Báo cáo vai trò riêng của bốn thành viên hiện có trong `report/`.
- [x] Không thấy credential pattern trong tracked source/report; `.env` không được commit.
- [ ] CP6: live demo/Q&A và xác nhận bảo vệ trước lớp.
- [ ] Từng thành viên tự nộp link repository trên VLearn LMS.
