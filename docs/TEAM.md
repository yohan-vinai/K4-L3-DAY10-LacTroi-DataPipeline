# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `LacTroi`
- **Mã Nhóm / Lớp:** `K4-L3-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3-DAY10-TenNhom-DataPipeline`

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | | | | Trưởng nhóm / Pipeline Integrator (`core/`, `phase1.py`, `corruption_flow.py`) | `report/<MSSV1>_HoTen.md` |
| 2 | | | | Data Foundation & Recovery (`crossref.py`, `cleaning.py`, raw data) | `report/<MSSV2>_HoTen.md` |
| 3 | Nguyễn Tiến Tuân | 2A202602595 | nguyentientuan2052000@gmail.com | RAG & Vector Index (`retrieval/index.py`, `embeddings.py`, ChromaDB), QA Agent (`agent.py`, `qa.py`) | `report/2A202602595_NguyenTienTuan.md` |
| 4 | | | | Observability & Evaluation (`quality.py` GX 1.x, `testset.py`, reporting) | `report/<MSSV4>_HoTen.md` |

*(Nếu nhóm có 3 hoặc 5-6 thành viên, xem bảng phân công chi tiết theo vai trò trong file `CHECKPOINTS.md`)*.

---

## # Cá nhân

### ## HoVaTen1-MSSV1
- **Vai trò:** Trưởng nhóm & Điều phối Pipeline.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập cấu hình hệ thống `core/config.py` và đường dẫn artifacts `core/utils.py`.
  - Kết nối luồng thực thi trong `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`.
  - Kiểm tra tính nhất quán của các artifacts và theo dõi Contributor tracking trên GitHub nhánh `main`.
- **Điều học được / Đóng góp chính:**
  - Hiểu sâu sắc về thiết kế Idempotent Pipeline và quản lý trạng thái luồng dữ liệu đa tầng.

### ## HoVaTen2-MSSV2
- **Vai trò:** Phụ trách Ingestion, Làm sạch & Phục hồi dữ liệu.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module thu thập Crossref API với cơ chế Fallback offline trong `src/ingestion/crossref.py`.
  - Chuẩn hóa schema, tính toán trường `age_days` và `text_for_embedding` trong `src/ingestion/cleaning.py`.
  - Thực thi cơ chế Idempotent Repair phục hồi dữ liệu từ raw snapshot.
- **Điều học được / Đóng góp chính:**
  - Kỹ thuật truy vết nguồn gốc dữ liệu (Data Lineage) và bảo toàn raw snapshot trước khi biến đổi.

### ## NguyenTienTuan-2A202602595
- **Vai trò:** Phụ trách RAG, Vector Database, Embedding & QA Agent.
- **Công việc chi tiết đã hoàn thành:**
  - `src/retrieval/index.py`: làm sạch metadata trước khi nạp ChromaDB (None/NaN/Timestamp làm crash `collection.add`), manifest lưu đường dẫn tương đối; quản lý 3 collection tách biệt `papers-baseline` / `papers-corrupted` / `papers-repaired` (HNSW cosine, MiniLM-L6-v2).
  - `src/retrieval/qa.py`: nhận diện loại câu hỏi theo gốc từ — sửa lỗi 5/10 câu testset bị định tuyến sai (Token F1 baseline 0.515 → 1.0).
  - `src/retrieval/agent.py`, `mock_llm.py`, `llm.py`: ReAct Agent 2 tools (`lookup_paper`, `semantic_search_papers`) với prompt chống bịa; mock LLM có tool-calling để agent chạy offline; `run_agent_demo()` ghi câu trả lời agent theo từng collection.
  - `src/retrieval/diagnostics.py`: `diagnose_agent_answers` + `build_probe_questions` đo Silent Failure (CP4: 8/16 câu, 7 câu trích sai bài); `compare_retrieval` chứng minh phục hồi (CP5: vector cosine 1.0, thứ hạng top-k trùng 100%).
  - `script/demo_three_collections.py`: demo cùng câu hỏi trên 3 collection cho CP6.
  - PR: #2 (CP2), #5 (CP3), #7 (CP4), #8 (CP5).
- **Điều học được / Đóng góp chính:**
  - Dữ liệu hỏng không làm agent báo lỗi mà làm nó trả lời tự tin từ tài liệu sai; phải kiểm tra cả nguồn trích dẫn, không chỉ nội dung câu trả lời, và cô lập các không gian vector để so sánh khách quan.

### ## HoVaTen4-MSSV4
- **Vai trò:** Phụ trách Data Observability & Benchmark Evaluation.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập Quality Gate theo chuẩn mới **Great Expectations 1.x** và giám sát Freshness SLA trong `src/observability/quality.py`.
  - Xây dựng bộ câu hỏi đánh giá chuẩn trong `src/evaluation/testset.py`.
  - Đo lường và xuất bảng đối chiếu 3 trạng thái vào `data/reports/corruption_report.md`.
- **Điều học được / Đóng góp chính:**
  - Cách thiết lập hệ thống cảnh báo sớm chặn đứng hiện tượng Silent Failure trước khi dữ liệu vào serving layer.
