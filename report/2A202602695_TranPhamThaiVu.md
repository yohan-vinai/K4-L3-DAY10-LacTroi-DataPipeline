# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Trần Phạm Thái Vũ          |
| MSSV               | 2A202602695                |
| Khóa/Lớp         | K4-L3A                     |
| Tên nhóm         | Lạc Trôi                   |
| Vai trò chính    | Trưởng nhóm / Pipeline Integrator & Điều phối Hệ thống |
| Repository         | https://github.com/yohan-vinai/K4-L3-DAY10-LacTroi-DataPipeline.git |
| Ngày hoàn thành | 2026-09-25                 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
|---|---|---|---|---|
| Core Configuration & Paths | `src/core/config.py`, `src/core/utils.py` | Biến môi trường `.env`, tham số dự án | Đối tượng `Settings`, dataclass `Paths`, helper I/O | Hoàn thành (100%) |
| Baseline Pipeline (Phase 1) | `src/pipelines/phase1.py`, `script/run_phase1.py` | Raw data, Cleaning, Index, QA, GX 1.x | 7 artifacts Phase 1, `baseline_metrics.json`, `phase1_report.md` | Hoàn thành (100%) |
| Corruption & Repair Flow | `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` | Clean data, Corruption logic, Raw snapshot | Báo cáo đối chiếu 3 trạng thái `corruption_report.md`, metrics 3 pha | Hoàn thành (100%) |
| Live Demo & Quản trị Git | Quản lý branch, PR merge, runner terminal | Mã nguồn toàn nhóm | Nhánh `contrib/elysszxje`, sẵn sàng Live Demo CP6 | Hoàn thành (100%) |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
|---|---|---|
| Nâng cấp Great Expectations 1.x Ephemeral API | Vũ Duy Điệp (`observability/quality.py`) | Khắc phục lỗi `sources.pandas_default` bằng `context.data_sources.add_pandas`, chạy trơn tru |
| Tích hợp Exact Title Match & QA Routing | Nguyễn Tiến Tuân (`retrieval/qa.py`) | QA Agent định tuyến chính xác giữa tìm kiếm tiêu đề và câu hỏi nội dung |
| Cố định kịch bản tiêm 6 lỗi dữ liệu | Võ Phú Hãn (`ingestion/corruption.py`) | Đảm bảo seed=42 tạo suy thoái chính xác, kích hoạt đúng cảnh báo Freshness SLA > 25% |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
|---|---|---|---|
| Thiết lập cấu hình toàn cục & file I/O | `src/core/config.py`, `src/core/utils.py` | Load `.env`, định nghĩa đường dẫn chuẩn xác cross-platform | Chạy smoke test và load_settings |
| Điều phối luồng Baseline Pipeline | `src/pipelines/phase1.py` | Chạy 8 bước tuần tự từ Ingestion -> Index -> QA -> GX 1.x -> Report | `python script/run_phase1.py` |
| Xây dựng luồng Corruption & Idempotent Repair | `src/pipelines/corruption_flow.py` | Đo lường Silent Failure -> Kích hoạt cảnh báo -> Phục hồi 100% -> Đối chiếu 3 pha | `python script/run_corruption_flow.py` |
| Tạo báo cáo đối chiếu định lượng | `data/reports/corruption_report.md` | Bảng so sánh 3 cột: Baseline vs Corrupted vs Repaired | Đọc trực tiếp file markdown kết quả |

**Output cụ thể tạo ra:**
Báo cáo đối chiếu [`data/reports/corruption_report.md`](../data/reports/corruption_report.md) thể hiện đầy đủ bức tranh định lượng:
- Baseline: Hit Rate 1.0, Token F1 1.0, Quality Gate True, Freshness True.
- Corrupted: Hit Rate 0.50, Token F1 0.6506, Quality Gate False, Freshness False (stale 27.27%).
- Repaired: Hit Rate 1.0, Token F1 1.0, Quality Gate True, Freshness True.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Một hệ thống RAG trong doanh nghiệp thường bị lỗi "ngắt quãng giữa chừng" khi các module làm việc độc lập (data ingester làm một kiểu, vector store lưu một kiểu, observability kiểm tra một kiểu). Nếu thiếu một Pipeline Integrator chuẩn hóa cấu hình và luồng thực thi, các thành viên sẽ bị xung đột về schema, ghi đè dữ liệu lẫn nhau và không thể tái lập thí nghiệm (reproducibility).

### Cách triển khai
1. **Thiết kế Single Source of Truth:** `src/core/config.py` gom toàn bộ cấu hình (LLM model, embedding model, top_k, freshness threshold, đường dẫn tương đối) vào một đối tượng `Settings` đóng băng (`frozen=True`).
2. **Quản lý không gian Vector độc lập:** Thay vì ghi đè vào một collection ChromaDB duy nhất, tôi cấu hình 3 collection biệt lập: `papers-baseline`, `papers-corrupted`, và `papers-repaired`. Điều này giúp việc đánh giá chéo giữa các trạng thái hoàn toàn khách quan.
3. **Hiện thực hóa Idempotent Pipeline:** Trong `src/pipelines/corruption_flow.py`, bước repair luôn đọc lại từ raw snapshot nguyên bản (`data/raw/crossref_records.json`), chạy lại `build_clean_dataframe` và re-index lại. Quá trình này độc lập với trạng thái hỏng hóc trước đó.

### Input, output và contract

| Thành phần | Mô tả |
|---|---|
| Input | Cấu hình dự án, danh sách raw records từ Ingestion, test set từ Evaluation |
| Output | Pipeline thực thi tự động, các file metrics và comparison reports |
| Module phụ thuộc | Toàn bộ các module con: `ingestion`, `observability`, `retrieval`, `evaluation` |
| Module sử dụng output | Giảng viên, người dùng cuối, thành viên trong nhóm theo dõi tiến độ |
| Điều kiện lỗi cần xử lý | Mất kết nối internet (fallback snapshot), thiếu file clean, lỗi encode Windows UTF-8 |

### Cách xác minh

```powershell
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe script/run_phase1.py
.\.venv\Scripts\python.exe script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Cả hai lệnh chạy tuần tự với exit code 0, in ra thông báo hoàn thành các bước, không sinh exception.
- **Kết quả thực tế:** Cả hai kịch bản chạy đạt 100% yêu cầu, in ra kết quả đối chiếu 3 trạng thái.
- **Artifact/log:** `data/reports/phase1_report.md` và `data/reports/corruption_report.md`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi đánh giá trạng thái Corrupted và Repaired, nhóm cần quyết định cách tổ chức dữ liệu trong ChromaDB: dùng chung 1 collection và xóa ghi đè, hay tạo 3 collection riêng biệt.
- **Các phương án đã cân nhắc:**
  1. *Phương án A:* Dùng chung 1 collection `papers` và gọi `delete_collection` mỗi lần chuyển trạng thái.
  2. *Phương án B:* Tạo 3 collection riêng biệt (`papers-baseline`, `papers-corrupted`, `papers-repaired`) và lưu kèm 3 manifest embeddings riêng biệt.
- **Phương án đã chọn:** Phương án B.
- **Lý do:** Đảm bảo tính toàn vẹn (Data Lineage) và cho phép audit độc lập bất kỳ lúc nào mà không cần phải chạy lại toàn bộ pipeline từ đầu. Nếu giảng viên muốn kiểm tra lại index của tập corrupted, dữ liệu vẫn còn nguyên vẹn trong thư mục `data/chroma/`.
- **Bằng chứng quyết định phù hợp:** Cả 3 collection đều tồn tại đồng thời, kiểm thử truy vấn độc lập trên từng collection cho kết quả nhất quán với bảng so sánh.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  UnicodeEncodeError: 'charmap' codec can't encode character '\u2013' in position ...
  ```
  Xuất hiện trên Windows PowerShell khi in tiêu đề bài báo khoa học hoặc ghi file JSON/Markdown chứa các ký tự đặc biệt (dấu gạch ngang en-dash, ký tự toán học).
- **Lệnh hoặc bước tái hiện:** Chạy `python script/run_phase1.py` trên Windows terminal với encoding mặc định `cp1252`.
- **Nguyên nhân gốc:** Windows PowerShell mặc định sử dụng codepage của hệ thống (CP1252 hoặc CP936) thay vì UTF-8 cho stdout và stderr, gây lỗi khi in các bài báo khoa học quốc tế.
- **Cách xử lý:**
  1. Trong `src/core/utils.py`, luôn chỉ định tường minh `encoding="utf-8"` trong mọi hàm `open()`, `read_text()`, `write_text()`, `write_json()`.
  2. Hướng dẫn toàn nhóm thiết lập biến môi trường `$env:PYTHONIOENCODING="utf-8"` trước khi chạy kịch bản Python.
- **Cách xác minh sau khi sửa:** Chạy lại toàn bộ `run_phase1.py` và `run_corruption_flow.py`, toàn bộ ký tự Unicode được xử lý trôi chảy không một lỗi nhỏ.
- **Điều học được:** Trong các hệ thống xử lý văn bản đa ngôn ngữ và tài liệu khoa học, việc chuẩn hóa encoding UTF-8 ở tầng I/O và terminal là yêu cầu tiên quyết hàng đầu.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu được lấy từ Crossref REST API qua truy vấn HTTP, lưu thành snapshot JSON thô để bảo toàn Data Lineage. Tiếp theo, module cleaning loại bỏ thẻ XML/JATS, chuẩn hóa khoảng trắng, trích xuất tác giả, tính toán `age_days` và ghép thành văn bản 5 phần `text_for_embedding`. Chuỗi này được đưa qua mô hình `sentence-transformers/all-MiniLM-L6-v2` để chuyển thành vector nhúng 384 chiều và lưu vào ChromaDB với không gian cosine similarity.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   `test_set.json` gồm 10 câu hỏi thuộc 4 nhóm nội dung. Mỗi câu hỏi gắn kèm `ground_truth_doc_ids` (DOI chuẩn) và `ground_truth` (câu trả lời chuẩn). Khi Agent truy vấn, hệ thống đo:
   - `Retrieval Hit Rate`: Tỷ lệ câu hỏi mà ít nhất 1 tài liệu trong top-4 trả về trùng với `ground_truth_doc_ids`.
   - `Token F1`: Độ trùng khớp tập từ giữa câu trả lời sinh ra và ground truth.
   - `LLM Judge`: Đánh giá tính đúng đắn ngữ nghĩa theo thang điểm 1-5.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - Quality checks (Great Expectations): Kiểm tra tính toàn vẹn tĩnh của cấu trúc dữ liệu (Schema & Value Constraints): không null, ID phải duy nhất, độ dài tóm tắt tối thiểu, số dòng hợp lệ.
   - Freshness SLA: Giám sát tính kịp thời theo thời gian (Temporal Validity): đo lường độ tuổi `age_days` của bài báo, báo động khi tỷ lệ bài báo cũ vượt quá ngưỡng cho phép (> 25%).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Đây là nguyên tắc biến số độc lập trong nghiên cứu thực nghiệm. Việc giữ cố định đề thi giúp đo lường chính xác và khách quan mức độ tác động của chất lượng dữ liệu lên AI Agent, loại bỏ sai số do độ khó của câu hỏi gây ra.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - Artifacts: File `papers_clean_repaired.csv` có đủ 24 dòng không trùng lặp, collection `papers-repaired` được tái lập, báo cáo `repaired_quality_report.json` và `repaired_freshness_report.json` đều ghi nhận `success: True` và `is_fresh: True`.
   - Metrics: Retrieval Hit Rate phục hồi từ 0.50 về 1.0, Token F1 phục hồi từ 0.65 về 1.0, Judge Accuracy đạt 1.0.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
|---|---:|---:|---:|---|
| `retrieval_hit_rate` | 1.0000 | 0.5000 | 1.0000 | Tụt dốc một nửa khi mất 20% bài báo mới; khôi phục hoàn toàn sau repair |
| `mean_token_f1` | 1.0000 | 0.6506 | 1.0000 | Mất tóm tắt và nhiễu rác làm giảm F1 nghiêm trọng; trở về 1.0 sau repair |
| `judge_accuracy` | 1.0000 | 0.7000 | 1.0000 | 3 câu hỏi trượt hoàn toàn nội dung; phục hồi 100% sau repair |
| `mean_judge_score` | 5.0000 | 3.4000 | 5.0000 | Chất lượng câu trả lời giảm sút rõ rệt; trở về điểm tuyệt đối 5/5 |
| Quality checks | True | False | True | Bắt lỗi duplicate và empty summary thành công; pass sau repair |
| Freshness status | True | False | True | Phát hiện stale ratio 27.27% > 25%; pass sau repair |

### Kết luận từ số liệu

1. **Chuỗi 1 (Corruption -> Degradation):** Tiêm lỗi xóa 20% bài báo và làm rỗng summary -> Great Expectations báo lỗi `expect_column_value_lengths_to_be_between` -> Retrieval Hit Rate rơi từ 1.0 xuống 0.50, Token F1 giảm từ 1.0 xuống 0.6506.
2. **Chuỗi 2 (Repair -> Recovery):** Kích hoạt cơ chế Idempotent Repair từ raw snapshot -> GX Quality Gate và Freshness SLA phục hồi trạng thái `True` -> RAG Agent phục hồi trọn vẹn 100% Hit Rate và Token F1 (1.0).

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
Kịch bản `drop_latest_records` (loại bỏ 20% bài báo mới nhất) ảnh hưởng nặng nề nhất đến Retrieval Hit Rate, vì khi tài liệu hoàn toàn không còn trong cơ sở dữ liệu vector, Agent hoàn toàn không có cơ hội truy hồi dù mô hình embedding có mạnh đến đâu.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Về Data Pipeline:** Pipeline phải được thiết kế theo nguyên lý Idempotent và bảo toàn Raw Lineage. Nếu không lưu trữ snapshot gốc, khi dữ liệu bị lỗi thì không có cách nào khôi phục tự động an toàn.
2. **Về Data Observability:** Data Observability không chỉ là viết vài câu lệnh `assert`, mà là thiết lập các Quality Gate có kiểm soát (như Great Expectations 1.x) để ngăn chặn dữ liệu bẩn tràn vào vector store trước khi serving.
3. **Về Ảnh hưởng đến AI Agent:** Silent Failure là rủi ro nguy hiểm nhất của RAG Agent. Agent không hề báo lỗi đỏ khi dữ liệu bẩn, mà vẫn tự tin sinh câu trả lời sai lệch gây nguy hại cho người dùng.

### Nếu có thêm thời gian
Tôi sẽ tích hợp công cụ Orchestration tự động như Prefect hoặc Apache Airflow để tự động hóa việc kích hoạt cảnh báo qua Slack/Webhook và tự động chạy luồng repair ngay khi Quality Gate bị vi phạm.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Phạm Thái Vũ  
**Ngày xác nhận:** 2026-09-25  
