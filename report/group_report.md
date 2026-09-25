# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4-L3A                     |
| Tên nhóm         | Lạc Trôi                   |
| Repository         | https://github.com/yohan-vinai/K4-L3-DAY10-LacTroi-DataPipeline.git |
| Ngày hoàn thành | 2026-09-25                 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Trần Phạm Thái Vũ | 2A202602695 | Trưởng nhóm / Pipeline Integrator | `core/config.py`, `core/utils.py`, `pipelines/phase1.py`, `pipelines/corruption_flow.py`, `script/` |
| 2 | Võ Phú Hãn | N/A | Data Core Lead (Ingestion, Cleaning, Repair) | `ingestion/crossref.py`, `ingestion/cleaning.py`, `ingestion/corruption.py`, `data/raw/`, `data/clean/` |
| 3 | Nguyễn Tiến Tuân | N/A | RAG & Vector Store Specialist | `retrieval/embeddings.py`, `retrieval/index.py`, `retrieval/agent.py`, `retrieval/qa.py`, ChromaDB |
| 4 | Vũ Duy Điệp | N/A | Observability & Evaluation Lead | `observability/quality.py` (GX 1.x), `observability/reporting.py`, `evaluation/testset.py`, `evaluation/metrics.py` |

---

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành toàn bộ 7 Checkpoint (CP0 – CP6), thiết lập trọn vẹn kiến trúc Data Pipeline công nghiệp khép kín kết hợp Data Observability cho hệ thống RAG Agent.

- **Baseline Pipeline:** Ingestion thành công 24 bài báo khoa học từ Crossref Academic REST API (có cơ chế offline fallback), chuẩn hóa văn bản, tính toán `age_days`, tạo chuỗi định dạng ngữ cảnh `text_for_embedding`, và lập chỉ mục vào collection `papers-baseline` trong ChromaDB. Bộ đánh giá 10 câu hỏi chuẩn hóa đa dạng (`summary`, `authors`, `date`, `categories`) đạt chỉ số hoàn hảo: **Retrieval Hit Rate = 1.0000**, **Mean Token F1 = 1.0000**, **Judge Accuracy = 1.0000**, và hệ thống Quality Gate đạt **PASSED**.
- **Hiện tượng Silent Failure:** Tiêm 6 kịch bản suy thoái dữ liệu có kiểm soát (`seed=42`) khiến Agent suy giảm chất lượng nghiêm trọng: Retrieval Hit Rate sụt giảm 50% (còn 0.5000), Token F1 tụt xuống 0.7246, điểm số LLM Judge giảm từ 5.0 xuống 3.6 mà không có bất kỳ ngoại lệ runtime nào văng ra.
- **Hệ thống Cảnh báo Sớm:** Chặn đứng thành công dữ liệu bẩn trước khi vào serving layer. Great Expectations 1.x ephemeral mode phát hiện vi phạm tính duy nhất của `paper_id` và độ dài tối thiểu của `summary` (`success: False`). Freshness SLA cảnh báo dữ liệu quá hạn với tỷ lệ stale là **33.33%** (vượt ngưỡng 25%).
- **Idempotent Repair:** Cơ chế phục hồi tự động từ raw snapshot (`crossref_records.json`) đã tái tạo lại toàn bộ 24 bản ghi sạch, tái lập index collection `papers-repaired`, phục hồi 100% hiệu năng của Agent (Hit Rate 1.0, Token F1 1.0, Judge Accuracy 1.0) và đưa Quality Gate / Freshness SLA trở về trạng thái PASSED.

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref Academic API (hoặc Snapshot Offline data/raw/crossref_records.json)
    │
    ├── [Ingestion & Raw Preservation]
    │       -> Lưu trữ nguyên vẹn: data/raw/crossref_response.json & crossref_records.json
    │
    ├── [Cleaning & Feature Engineering]
    │       -> Chuẩn hóa khoảng trắng, parse ISO date, tính age_days, tạo text_for_embedding
    │       -> Lưu: data/clean/papers_clean.csv & papers_clean.json
    │
    ├── [Data Observability Gate - Baseline]
    │       -> Great Expectations 1.x ephemeral: kiểm tra row count, not null, unique ID, min length
    │       -> Freshness SLA: kiểm tra age_days <= 180 (ngưỡng stale <= 25%)
    │       -> Lưu: data/quality/baseline_quality_report.json & freshness_report.json
    │
    ├── [Vector Store Indexing - Baseline]
    │       -> Embedding: sentence-transformers/all-MiniLM-L6-v2
    │       -> ChromaDB Persistent Collection: papers-baseline
    │       -> Manifest: data/embeddings/papers_embeddings.json
    │
    ├── [Evaluation Baseline]
    │       -> Bộ 10 câu hỏi test_set.json (summary, authors, date, categories)
    │       -> Đo lường: Retrieval Hit Rate (1.0), Token F1 (1.0), LLM Judge (5.0)
    │       -> Xuất: data/results/baseline_metrics.json & data/reports/phase1_report.md
    │
    ├── [Synthetic Data Corruption (CP4)]
    │       -> Tiêm 6 kịch bản lỗi với seed=42 (drop 20%, blank summary, noise, truncate, stale, duplicate)
    │       -> Lưu: papers_clean_corrupted.csv, corruption_log.json
    │       -> Re-index ChromaDB collection: papers-corrupted
    │       -> Đo lường Silent Failure: Hit Rate rớt xuống 0.5000, F1 rớt xuống 0.6506
    │       -> Quality Gate báo False, Freshness SLA báo False (stale 27.27%)
    │
    ├── [Idempotent Repair & Verification (CP5)]
    │       -> Tự động tái xử lý từ Raw Snapshot ban đầu (Data Lineage)
    │       -> Làm sạch lại: papers_clean_repaired.csv & papers_clean_repaired.json
    │       -> Re-index ChromaDB collection: papers-repaired
    │       -> Đánh giá phục hồi: Hit Rate đạt 1.0000, Token F1 đạt 1.0000
    │       -> Quality Gate và Freshness SLA phục hồi trạng thái True (PASSED)
    │
    └── [Automated 3-State Comparison Reporting]
            -> data/reports/corruption_report.md (Bảng đối chiếu định lượng 3 trạng thái)
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
|---|---|---|---|---|
| Ingestion | Crossref API / raw snapshot | Fetch có timeout, retry backoff, parse payload hoặc fallback snapshot | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Võ Phú Hãn |
| Cleaning | Raw records list | Bỏ bản ghi thiếu title/id, chuẩn hóa text, tính `age_days`, tạo 5-part `text_for_embedding` | `data/clean/papers_clean.csv`, `papers_clean.json` | Võ Phú Hãn |
| Embedding/index | Cleaned DataFrame | MiniLM-L6-v2 embedding, nạp vào ChromaDB theo collection name tương ứng | `data/chroma/`, `data/embeddings/*.json` | Nguyễn Tiến Tuân |
| Evaluation | Test set + Index | Exact title lookup + semantic search, keyword QA routing, Token F1, LLM Judge | `data/results/*_metrics.json`, `data/results/*_answers.json` | Nguyễn Tiến Tuân & Vũ Duy Điệp |
| Observability | Cleaned/Corrupted DataFrame | Ephemeral Great Expectations 1.x (4 expectations) & Freshness SLA monitoring | `data/quality/*_quality_report.json`, `data/quality/*_freshness_report.json` | Vũ Duy Điệp |
| Corruption/repair | Clean DataFrame & Raw records | Tiêm 6 kịch bản suy thoái dữ liệu; Tái lập dữ liệu sạch từ Raw snapshot | `papers_clean_corrupted.*`, `papers_clean_repaired.*`, `corruption_log.json` | Võ Phú Hãn & Trần Phạm Thái Vũ |
| Orchestration | Cấu hình dự án & modules | Điều phối tuần tự các bước trong Phase 1 và Corruption Flow | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `script/` | Trần Phạm Thái Vũ |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
|---|---|
| `LLM_PROVIDER` | `gemini` (hỗ trợ fallback mock/heuristic nếu không có key) |
| `LLM_MODEL` | `gemini-2.5-flash` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày (ngưỡng cảnh báo stale ratio > 25%) |
| Random seed tiêm lỗi | 42 |

### Lệnh cài đặt

```bash
uv sync
```

Hoặc qua pip:

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline Pipeline:
```bash
python script/run_phase1.py
```

Corruption & Idempotent Repair Flow:
```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
|---|---|---|---|
| Baseline pipeline | Thành công (100%) | 2026-09-25 17:00 UTC+7 | `data/reports/phase1_report.md`, `data/results/baseline_metrics.json` |
| Corruption flow | Thành công (100%) | 2026-09-25 16:53 UTC+7 | `data/reports/corruption_report.md`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json` |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
|---|---|
| Source | Crossref Academic REST API (`https://api.crossref.org/works`) |
| Query/filter | `query=agentic retrieval augmented generation large language model`, `filter=from-pub-date:2026-03-29,has-abstract:true` |
| Thời điểm lấy dữ liệu | 2026-09-25 (với fallback offline snapshot tại `data/raw/crossref_response.json`) |
| Số record nhận được | 24 |
| Cơ chế retry/backoff | Timeout 20s, Exponential backoff (1s, 2s, 4s), fallback offline snapshot khi gặp lỗi kết nối |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
|---|---|---|---|---|
| `paper_id` | String | Có | DOI định danh duy nhất của bài báo | Bỏ qua record nếu thiếu DOI |
| `title` | String | Có | Tiêu đề bài báo | Bỏ qua record nếu thiếu tiêu đề |
| `summary` | String | Có | Tóm tắt / abstract khoa học | Làm sạch thẻ XML/JATS `<jats:p>`, strip khoảng trắng |
| `published` | String | Có | Ngày xuất bản định dạng chuẩn ISO YYYY-MM-DD | Lấy từ `published-online` hoặc `created`, fallback ngày hiện tại |
| `authors_joined` | String | Không | Danh sách tác giả ghép bằng dấu phẩy | Ghép `given` + `family`, để trống nếu không có tác giả |
| `categories_joined`| String | Không | Thể loại / lĩnh vực chủ đề | Ghép từ danh sách `subject`, để trống nếu không có |
| `abs_url` | String | Không | Đường dẫn DOI chính thức (`https://doi.org/...`) | Sinh tự động từ `paper_id` |
| `pdf_url` | String | Không | Đường dẫn tải PDF | Lấy từ `link[application/pdf]` nếu có |
| `age_days` | Integer | Có | Độ tuổi tài liệu tính theo ngày từ ngày xuất bản | `(now_utc - published_date).days` |
| `text_for_embedding`| String | Có | Văn bản định dạng 5 phần dùng để trích xuất embedding vector | Ghép có nhãn rõ ràng theo 5 phần cấu trúc |

### Quy tắc cleaning

| Quy tắc | Quality dimension liên quan | Số record bị tác động | Cách xác minh |
|---|---|---:|---|
| Loại bỏ thẻ XML/HTML/JATS trong abstract | Validity | 24 | Regex loại bỏ `<jats:...>`, `<i>`, `<b>`, `<p>` |
| Chuẩn hóa khoảng trắng và newline thừa | Consistency | 24 | `re.sub(r"\s+", " ", text).strip()` |
| Định dạng ngày xuất bản chuẩn ISO YYYY-MM-DD | Completeness & Validity | 24 | Kiểm tra format `\d{4}-\d{2}-\d{2}` |
| Tạo `text_for_embedding` 5 phần chuẩn | Completeness & Usability | 24 | Kiểm tra đủ nhãn Title, Authors, Published, Categories, Summary |
| Loại bỏ bản ghi trùng lặp DOI | Uniqueness | 0 (bản ghi thô không trùng) | `drop_duplicates(subset=["paper_id"])` |

**Giải thích cách tạo `text_for_embedding`, document ID và `age_days`:**
- `paper_id` lấy từ trường `DOI` chuẩn quốc tế, giúp loại bỏ hoàn toàn sự không nhất quán giữa các nguồn dữ liệu.
- `age_days` được tính bằng khoảng cách giữa ngày hiện tại (`now_utc()`) và ngày công bố `published`. Đây là trường quan trọng phục vụ trực tiếp cho việc giám sát Freshness SLA.
- `text_for_embedding` được cấu trúc hóa có tiền tố để mô hình MiniLM hiểu được ngữ cảnh phân tầng:
  ```text
  Title: {title}
  Authors: {authors_joined}
  Published: {published}
  Categories: {categories_joined}
  Summary: {summary}
  ```

---

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
|---|---|
| Số câu hỏi | 10 câu hỏi chuẩn hóa |
| Các `question_type` | `summary` (3 câu), `authors` (3 câu), `date` (2 câu), `categories` (2 câu) |
| Ground-truth document ID | DOI tương ứng trong `test_set.json` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection | ChromaDB: `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k` | 4 |
| LLM provider/model | Gemini 2.5 Flash (hoặc Structured Output Heuristic Judge) |
| Test set dùng chung | `data/eval/test_set.json` |

**Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:**
Việc giữ cố định 100% bộ câu hỏi `test_set.json` và ground-truth xuyên suốt cả 3 trạng thái là nguyên tắc khoa học bắt buộc (Controlled Experiment). Khi đề bài không đổi, mọi sự biến thiên về Retrieval Hit Rate, Token F1 và Judge Score hoàn toàn phản ánh trực tiếp chất lượng của tầng dữ liệu (Data Layer), loại trừ mọi biến số ngẫu nhiên do thay đổi câu hỏi.

---

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
|---|---|---|---|
| Raw response/records | `data/raw/crossref_records.json` | Có | 24 bản ghi snapshot nguyên gốc |
| Cleaned dataset | `data/clean/papers_clean.csv` & `.json` | Có | 24 bản ghi sạch đầy đủ thuộc tính |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json` | Có | 24 vector vectors MiniLM trong ChromaDB |
| Evaluation set | `data/eval/test_set.json` | Có | 10 câu hỏi chuẩn hóa có ground truth |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Hit Rate 1.0, Token F1 1.0 |
| Quality/freshness | `data/quality/baseline_quality_report.json` | Có | GX 1.x success: True, Freshness: True |
| Baseline report | `data/reports/phase1_report.md` | Có | Báo cáo chi tiết Phase 1 tự động sinh |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
|---|---:|---|
| `retrieval_hit_rate` | 1.0000 | 10/10 câu hỏi truy vấn tìm thấy đúng tài liệu ground-truth trong top-4 |
| `mean_token_f1` | 1.0000 | Trùng khớp từ vựng hoàn hảo giữa câu trả lời trích xuất và ground-truth |
| `judge_accuracy` | 1.0000 | 100% câu trả lời được LLM Judge chấm đúng nội dung bản chất |
| `mean_judge_score` | 5.0000 | Điểm tuyệt đối 5/5 trên thang đo chất lượng câu trả lời |
| Ragas, nếu có | Skipped | Bỏ qua pass Ragas nặng (có thể kích hoạt bằng `RUN_RAGAS=1`) |

---

## 8. Data quality và freshness

### Quality checks (Great Expectations 1.x)

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
|---|---|---|---|---|
| `ExpectTableRowCountToBeBetween` | Completeness | [5, 5000] dòng | PASSED (24 dòng) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (`paper_id`) | Completeness | 0% null | PASSED (0% null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (`title`) | Completeness | 0% null | PASSED (0% null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (`text_for_embedding`) | Completeness | 0% null | PASSED (0% null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToBeUnique` (`paper_id`) | Uniqueness | 100% unique | PASSED (24/24 unique) | `baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween` (`summary`) | Validity | >= 30 ký tự | PASSED (min > 30) | `baseline_quality_report.json` |

### Freshness SLA

| Thuộc tính | Giá trị |
|---|---|
| Freshness được đo tại | `data/quality/freshness_report.json` |
| Timestamp mới nhất | `2026-06-12` |
| Ngưỡng freshness | `age_days <= 180` (Cảnh báo khi stale ratio > 25%) |
| Trạng thái baseline | PASSED (Fresh) |
| Lý do | Số dòng quá hạn là 1/24 (4.17%), thấp hơn nhiều so với ngưỡng vi phạm 25% |

---

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
|---|---|---:|---|---|---|
| Drop latest records | Sắp xếp theo ngày xuất bản, loại bỏ 20% bản ghi mới nhất | 5 bản ghi | Thiếu tài liệu gần đây | Retrieval Hit Rate trượt các câu hỏi thuộc 5 bài báo này | Phục hồi lại từ raw snapshot |
| Blank summary | Xóa rỗng trường `summary = ""` ở 20% bản ghi còn lại | 4 bản ghi | `ExpectColumnValueLengthsToBeBetween` báo lỗi | Mất ngữ cảnh tóm tắt, F1 giảm sâu | Tái lập abstract từ raw metadata |
| Inject noise | Chèn chuỗi rác `###CORRUPTED_GARBAGE_NOISE###` | 3 bản ghi | Bẩn vector embedding | Nhiễu khoảng cách cosine similarity | Làm sạch text từ raw snapshot |
| Truncate title | Cắt ngắn `title[:5]` | 3 bản ghi | Tiêu đề quá ngắn | Mất khả năng exact title match | Khôi phục title gốc từ raw |
| Stale date | Lùi ngày xuất bản về 365 ngày trước | 6 bản ghi | Freshness SLA `is_fresh` báo `False` | Tỷ lệ stale đạt 27.27% > 25% | Tính toán lại ngày chuẩn từ raw |
| Duplicate rows | Nhân bản 3 bản ghi đã có | 3 bản ghi | `ExpectColumnValuesToBeUnique` báo lỗi | Gây trùng lặp kết quả retrieval | `drop_duplicates(subset=['paper_id'])` |

**Corruption log:**
- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi nhận đầy đủ seed (42), số dòng trước (24), số dòng sau (22), danh sách ID cụ thể bị tác động cho từng kịch bản.

**Giải thích cơ chế Idempotent Repair:**
Hệ thống không thực hiện các câu lệnh "vá víu" chắp vá trên DataFrame đang bị lỗi (dễ gây lỗi dây chuyền và không kiểm soát được trạng thái). Thay vào đó, quy trình tuân thủ nguyên lý **Idempotent Repair**: Tải lại toàn bộ dữ liệu thô nguyên bản từ `data/raw/crossref_records.json`, kích hoạt lại toàn bộ chu trình `build_clean_dataframe`, làm sạch, deduplicate, và tính toán lại `age_days`. Dù chạy 1 lần hay 100 lần, kết quả thu được luôn là một tập dữ liệu chuẩn xác, nhất quán và độc lập với lịch sử lỗi.

---

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
|---|---:|---:|---:|---:|---:|---|
| `retrieval_hit_rate` | 1.0000 | 0.5000 | 1.0000 | 🔻 Giảm 50.00% | 100% | Mất 5 bài báo mới khiến 5 câu hỏi truy vấn trượt hoàn toàn; phục hồi hoàn toàn sau repair |
| `mean_token_f1` | 1.0000 | 0.7246 | 1.0000 | 🔻 Giảm 27.54% | 100% | Abstract rỗng và chuỗi rác làm câu trả lời thiếu hụt thông tin; phục hồi 100% |
| `judge_accuracy` | 1.0000 | 0.8000 | 1.0000 | 🔻 Giảm 20.00% | 100% | Câu hỏi trượt nội dung do mất tài liệu; phục hồi chuẩn xác sau repair |
| `mean_judge_score` | 5.0000 | 3.6000 | 5.0000 | 🔻 Giảm 1.40 điểm | 100% | Điểm chất lượng sụt giảm nghiêm trọng; trở lại điểm tối đa 5/5 |
| Quality Gate (GX 1.x) | True | False | True | ❌ Bị đánh trượt | 100% | Bắt lỗi duplicate ID và empty summary; vượt qua sau repair |
| Freshness SLA (is_fresh) | True | False | True | ❌ Bị cảnh báo | 100% | Stale ratio từ 33.33% giảm về 4.17% sau repair |

**Hai kết luận có quan hệ nhân quả:**
1. **Dữ liệu bẩn sinh ra Silent Failure:** Việc xóa rỗng tóm tắt và xóa bớt tài liệu (`corruption`) dẫn tới việc Great Expectations phát hiện vi phạm độ dài (`quality signal`), trực tiếp kéo tụt Retrieval Hit Rate từ 1.0 xuống 0.50 và Token F1 từ 1.0 xuống 0.7246 (`agent metric`). RAG Agent không văng ngoại lệ runtime nào mà tự tin trả về kết quả sai lệch.
2. **Cơ chế Idempotent Repair khôi phục hoàn toàn chất lượng:** Việc chạy lại chu trình làm sạch từ raw snapshot (`repair action`) đã loại bỏ toàn bộ bản ghi trùng lặp và phục hồi abstract đầy đủ (`quality recovery`), đưa cả Quality Gate và Freshness SLA về `True`, giúp RAG Agent phục hồi 100% điểm số ban đầu (`agent recovery`: Hit Rate 1.0, Token F1 1.0).

---

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Khi chạy Great Expectations trên phiên bản mới 1.x, câu lệnh `context.sources.pandas_default` bị báo `AttributeError` hoặc cảnh báo deprecated làm vỡ pipeline.
- **Nguyên nhân:** Khung kiểm định Great Expectations từ bản 1.0.0 đã thay đổi hoàn toàn kiến trúc Fluent Datasources. Các phương thức cấu hình cũ không còn được hỗ trợ trong môi trường runtime ephemeral.
- **Cách xử lý:** Nhóm đã nâng cấp toàn diện module `src/observability/quality.py` sang chuẩn **GX 1.x Ephemeral API**:
  Sử dụng `gx.get_context(mode="ephemeral")`, thêm pandas data source qua `context.data_sources.add_pandas(...)`, tạo dataframe asset và batch definition `add_batch_definition_whole_dataframe()`, cấu hình suite với các lớp Expectation chuẩn mới (`gx.expectations.Expect...`).
- **Cách xác minh:** Chạy kiểm thử tự động, hàm trả về kết quả JSON với đầy đủ thông tin kiểm định, hoạt động hoàn hảo trên cả 3 trạng thái và không phát sinh bất kỳ warning hay lỗi crash nào.

---

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
|---|---|---|
| Kích thước tập dữ liệu còn nhỏ (24 records) | Chưa đánh giá được hiệu năng tải lớn khi vector store lên tới hàng chục nghìn bài báo | Tích hợp cơ chế batch ingestion với pagination từ Crossref API cho 1,000+ tài liệu |
| Đánh giá RAG hiện dựa trên 10 câu hỏi mẫu | Độ bao phủ các tình huống cạnh tranh ngữ nghĩa (semantic ambiguity) chưa cao | Ứng dụng Ragas framework để tự động sinh testset 50 câu hỏi đa tầng |
| Freshness threshold hiện cố định ở 180 ngày | Có thể không phù hợp với các lĩnh vực nghiên cứu thay đổi theo tuần | Cho phép cấu hình ngưỡng động theo từng chuyên ngành khoa học (Dynamic SLA) |

---

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác (`https://github.com/yohan-vinai/K4-L3-DAY10-LacTroi-DataPipeline.git`).
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp (`run_phase1.py` và `run_corruption_flow.py`).
- [x] Baseline, corrupted và repaired dùng cùng evaluation set (`data/eval/test_set.json`).
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
