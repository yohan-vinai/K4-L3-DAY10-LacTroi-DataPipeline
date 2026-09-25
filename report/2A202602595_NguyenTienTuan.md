# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Tiến Tuân |
| MSSV               | 2A202602595 |
| Khóa/Lớp         | K4 |
| Tên nhóm         | LacTroi |
| Vai trò chính    | RAG, Vector Index & QA Agent Specialist |
| Repository         | https://github.com/yohan-vinai/K4-L3-DAY10-LacTroi-DataPipeline |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Vector index ChromaDB (3 collection tách biệt) | `src/retrieval/index.py` — `LocalEmbeddingIndex.build/load/search/lookup` | Clean/corrupted/repaired DataFrame (Hãn) | `papers-baseline`, `papers-corrupted`, `papers-repaired` + manifest `data/embeddings/*.json` | Hoàn thành (PR #2) |
| Trả lời câu hỏi cho evaluation | `src/retrieval/qa.py` — `answer_question`, `_question_type` | `test_set.json` (Điệp) | Câu trả lời + `retrieved_doc_ids` cho `evaluate_pipeline` | Hoàn thành (PR #2) |
| ReAct QA Agent + mock offline | `src/retrieval/agent.py`, `src/retrieval/mock_llm.py`, `src/retrieval/llm.py` | Index + `LLM_PROVIDER` | `run_agent_demo()` → `agent_demo_answers.json`, câu trả lời agent cho corrupted/repaired | Hoàn thành (PR #5) |
| Phân tích Silent Failure (CP4) | `src/retrieval/diagnostics.py` — `diagnose_agent_answers`, `build_probe_questions` | Câu trả lời agent 2 collection + `corruption_log.json` | Báo cáo silent failure / wrong source theo từng câu | Code xong (PR #7), chờ tích hợp vào pipeline |
| Chứng minh phục hồi retrieval (CP5) | `src/retrieval/diagnostics.py` — `compare_retrieval` | Index baseline + index candidate | Độ khớp vector và thứ hạng top-k | Code xong (PR #8), chờ tích hợp vào pipeline |
| Demo 3 collection (CP6) | `script/demo_three_collections.py` | 3 manifest sau khi chạy 2 pipeline | In cùng câu hỏi trên baseline/corrupted/repaired | Hoàn thành, test trên thư mục tạm |

`embeddings.py` (MiniLM, `normalize_embeddings=True`) có sẵn trong starter repo; tôi kiểm tra và dùng lại, không viết mới.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Thống nhất contract clean schema | Võ Phú Hãn — `cleaning.py` | `published` dạng chuỗi `YYYY-MM-DD`, `authors_joined`/`categories_joined` nối bằng `", "`; index build thẳng từ `papers_clean.json` không lỗi |
| Tích hợp testset với QA | Vũ Duy Điệp — `testset.py` | Phát hiện 5/10 câu bị định tuyến sai loại câu hỏi; sửa phía `qa.py`, F1 baseline 0.515 → 1.0 |
| Rà soát nhánh pipeline | Trần Phạm Thái Vũ, Vũ Duy Điệp — `pipelines/` | Phát hiện nhánh pipeline xung đột 11 file với `main`, agent chưa được gọi, và Freshness SLA không bật trên dữ liệu lỗi |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Làm sạch metadata trước khi nạp ChromaDB | `index.py` — `_to_text`, `METADATA_FIELDS` | Không crash khi có `None`/`NaN`/`Timestamp` | Build với dữ liệu cố ý chứa 3 loại giá trị → 24 docs |
| Manifest dùng đường dẫn tương đối | `index.py` — `build`, `load` | `persist_path: "data/chroma"` | Đọc lại manifest và `load()` trên thư mục khác |
| Nhận diện loại câu hỏi bền vững | `qa.py` — `_question_type` | Hit 1.0, F1 1.0 trên testset nhóm | `evaluate_pipeline` trên `data/eval/test_set.json` |
| Agent chạy offline có tool-calling | `mock_llm.py`, `agent.py` | 0 lỗi agent trên 3 collection × 16 câu | `run_agent_demo` với `LLM_PROVIDER=mock` |
| Đo Silent Failure và phục hồi | `diagnostics.py` | Số liệu ở mục 8 | `diagnose_agent_answers`, `compare_retrieval` |

Output cụ thể: với câu *"When was 'Agentic Retrieval-Augmented Generation for Knowledge-Intensive Tasks' published?"*, agent trả lời `2026-05-20` trên baseline, `2025-09-25` trên corrupted (đúng bài, sai ngày, không cảnh báo) và lại `2026-05-20` trên repaired (`script/demo_three_collections.py`).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần retrieval là nơi dữ liệu bẩn biến thành câu trả lời sai. Tôi cần (1) nạp ba phiên bản dữ liệu vào ba không gian vector độc lập để so sánh khách quan, (2) cho agent trả lời chỉ dựa trên corpus, và (3) đo được khi nào agent "tự tin nhưng sai" — Silent Failure — thay vì chỉ nhìn metric tổng.

### Cách triển khai

- **Index:** mỗi dòng DataFrame thành một document; nội dung embed là `text_for_embedding` 5 phần; metadata ép về chuỗi vì ChromaDB từ chối `None` và `Timestamp`. `record_id = paper_id::vị trí` nên các dòng trùng `paper_id` (lỗi duplicate) vẫn nạp được. Collection dùng HNSW cosine; vector MiniLM đã chuẩn hóa L2 nên cosine = tích vô hướng, `score = 1 - distance`. Tên collection suy ra từ đường dẫn manifest nên baseline không bao giờ bị ghi đè khi build corrupted/repaired.
- **QA cho evaluation:** nếu câu hỏi có tiêu đề trong nháy đơn thì `lookup` chính xác trước, sau đó ghép với semantic search; trường trả lời chọn theo loại câu hỏi (tác giả / ngày / danh mục / câu đầu summary). Loại câu hỏi nhận theo gốc từ sau khi bỏ phần tiêu đề, để tiêu đề chứa chữ "Author" không làm lệch.
- **Agent:** `create_agent` với 2 tool `lookup_paper` và `semantic_search_papers`; prompt bắt buộc gọi tool, lookup trước search, trích `paper_id`, nói "không tìm thấy" thay vì đoán. Mock LLM mô phỏng đúng vòng ReAct này để demo chạy không cần API key.
- **Silent Failure:** một câu là silent failure khi câu trả lời sai **hoặc trích sai bài**, mà không thừa nhận thiếu dữ liệu. Tiêu chí "sai nguồn" là cần thiết vì corpus có các cặp bài gần trùng ("X" và "Advanced Perspectives on X") cùng tác giả, cùng summary.
- **Phục hồi:** so sánh hai mức — vector từng bài (cosine giữa hai collection) và thứ hạng top-k từng câu hỏi.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | DataFrame có `paper_id, title, published, authors_joined, categories_joined, summary, abs_url, pdf_url, text_for_embedding`; `test_set.json` (id, question_type, question, ground_truth, ground_truth_doc_ids); `corruption_log.json` (`corruptions[].type/paper_ids`) |
| Output | 3 collection ChromaDB; manifest `data/embeddings/papers_embeddings{,_corrupted,_repaired}.json`; `AnswerResult`; danh sách câu trả lời agent; báo cáo `diagnose_agent_answers` / `compare_retrieval` |
| Module phụ thuộc | `ingestion/cleaning.py`, `ingestion/corruption.py`, `evaluation/testset.py`, `core/config.py` |
| Module sử dụng output | `evaluation/metrics.py`, `pipelines/phase1.py`, `pipelines/corruption_flow.py` |
| Điều kiện lỗi cần xử lý | Metadata `None/NaN/Timestamp`; `paper_id` trùng; summary rỗng; tiêu đề bị cắt (lookup miss → search); provider lỗi/429 (ghi `error`, không dừng pipeline); chạy trên máy khác (đường dẫn tương đối) |

### Cách xác minh

```bash
source .venv/bin/activate
export LLM_PROVIDER=mock
python -c "import pandas as pd; from core.config import load_settings; from retrieval.index import LocalEmbeddingIndex; s=load_settings(); df=pd.read_json(s.paths.clean_json, dtype={'published':str}); i=LocalEmbeddingIndex.build(df, s); print(i.collection_name, i.collection.count())"
python script/demo_three_collections.py
```

- **Kết quả mong đợi:** `papers-baseline 24`; demo in câu trả lời của 3 collection, corrupted sai ở truncate_title / drop_latest / stale_date / blank_summary, repaired trùng baseline.
- **Kết quả thực tế:** đúng như trên khi chạy trong thư mục tạm (bản sao `data/raw`, `data/clean`). Pipeline chính thức của nhóm chưa merge vào `main` nên chưa có artifact cuối trong repo.
- **Artifact/log:** `data/results/agent_demo_answers.json` và các file diagnostics sẽ được sinh khi `corruption_flow.py` gọi các hàm ở PR #7/#8.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** trên dữ liệu lỗi, agent vẫn trả lời "đúng" 8/10 câu nếu chỉ so nội dung với ground truth, dù Hit Rate tụt từ 1.0 xuống 0.6.
- **Các phương án đã cân nhắc:** (a) chỉ chấm nội dung câu trả lời; (b) chấm theo `retrieval_hit` của bộ QA; (c) chấm nội dung **và** kiểm tra bài được trích dẫn có phải bài đích không.
- **Phương án đã chọn:** (c) — thêm `wrong_source` vào định nghĩa Silent Failure.
- **Lý do:** corpus có cặp bài gần trùng; khi bài đích bị drop hoặc bị cắt tiêu đề, agent lấy bài "sinh đôi" nên nội dung trùng khớp nhưng nguồn sai. Phương án (a) che mất lỗi; (b) không phản ánh agent. Trade-off: (c) phụ thuộc vào việc agent trích DOI — mock luôn trích, LLM thật được prompt yêu cầu nhưng chưa được kiểm chứng.
- **Bằng chứng:** trên 16 câu (10 testset + 6 probe), accuracy nội dung corrupted = 0.75 nhưng có 8 silent failure, trong đó 7 câu trích sai bài (ví dụ `Bao Do, Linh Ngo (source: …3671816)` thay vì `…3671804`).

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** baseline Hit Rate = 1.0 nhưng `mean_token_f1 = 0.515`, `judge_accuracy = 0.5`; các câu `authors`/`categories` có F1 = 0.00, câu trả lời là một câu tóm tắt.
- **Lệnh tái hiện:** `evaluate_pipeline` trên `data/eval/test_set.json` bản đầu của nhóm với `qa.py` gốc.
- **Nguyên nhân gốc:** `qa._extract_answer` chỉ nhận cụm cố định `"who authored"` và `"what categories"`, còn testset hỏi *"Who are the authors of…"* và *"What are the categories of…"* → rơi xuống nhánh summary. Retrieval đúng bài, chỉ lấy nhầm trường.
- **Cách xử lý:** thêm `_question_type()` nhận theo gốc từ (`author`, `date`/`year`, `categor`/`field`…) sau khi bỏ tiêu đề trong nháy.
- **Cách xác minh sau khi sửa:** chạy lại trên cùng testset → Hit 1.0, F1 1.0, judge accuracy 1.0; câu thử có tiêu đề chứa "Authorship Dating of Categories" vẫn nhận đúng là `summary`.
- **Điều học được:** lỗi ở ranh giới giữa hai module không làm crash mà làm metric thấp một cách "hợp lý" — cũng là một dạng silent failure. Phải chạy thử tích hợp sớm thay vì chỉ test từng module.

## 7. Hiểu biết về luồng end-to-end

1. **Crossref → vector index:** API (hoặc snapshot offline khi lỗi mạng/429) trả JSON thô, lưu nguyên `crossref_response.json` và bản parse `crossref_records.json`. Cleaning chuẩn hóa text, bỏ XML, tính `age_days`, khử trùng `paper_id`, ghép `text_for_embedding`. Index embed trường này bằng MiniLM rồi nạp vào ChromaDB kèm metadata.
2. **Evaluation set:** mỗi câu có `ground_truth_doc_ids`; Hit Rate = tỷ lệ câu mà một trong top-k tài liệu truy xuất là bài đích; Token F1 so từ giữa câu trả lời và `ground_truth`; judge chấm 1–5 (mock dùng heuristic theo F1).
3. **Quality vs freshness:** quality check (GX 1.x) kiểm tra tính hợp lệ cấu trúc của từng lô — số dòng, null, `paper_id` duy nhất, độ dài summary. Freshness đo độ cũ của dữ liệu theo thời gian (tỷ lệ `age_days > 180` so với ngưỡng 25%). Dữ liệu có thể hợp lệ nhưng cũ, hoặc mới nhưng hỏng.
4. **Cùng test set:** chỉ khi câu hỏi và ground truth giữ nguyên thì chênh lệch metric mới phản ánh thay đổi của dữ liệu, không phải của đề thi.
5. **Repair thành công** khi: GX pass trở lại, dữ liệu repaired trùng dữ liệu sạch (trừ `age_days`), metrics trở về bằng baseline, vector từng bài trùng hoàn toàn (cosine 1.0) và thứ hạng top-k giống hệt baseline.

## 8. Phân tích kết quả

> Nguồn số liệu: tôi tự chạy với `LLM_PROVIDER=mock` trên code của `main` (cleaning/corruption của Hãn seed 42, testset và quality của Điệp, `repair_clean_from_raw` của Hãn) trong thư mục tạm, ngày 2026-09-25. Pipeline chính thức của nhóm chưa merge nên `corruption_report.md` cuối có thể khác; nếu khác, số của pipeline chính thức là số chấm điểm.

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0 | 0.6 | 1.0 | 4 bài đích bị drop, 1 bài bị cắt tiêu đề → lookup trượt |
| `mean_token_f1` | 1.0 | 0.753 | 1.0 | Giảm ít hơn Hit Rate vì bài "sinh đôi" có cùng tác giả/summary |
| `judge_accuracy` | 1.0 | 0.8 | 1.0 | Judge heuristic (mock), dựa trên F1 |
| `mean_judge_score` | 5 | 3.8 | 5 | |
| Quality checks (GX 1.x) | Pass 6/6 | **Fail 4/6** | Pass 6/6 | Vi phạm: `paper_id` không duy nhất (6 dòng), độ dài `summary` (4 dòng rỗng) |
| Freshness status | `is_fresh=True` (0.042) | **`is_fresh=True` (0.227)** | `is_fresh=True` (0.042) | Có 5/22 dòng cũ nhưng chưa vượt ngưỡng 25% → SLA **không cảnh báo** |

Chỉ số riêng của phần retrieval (16 câu = 10 testset + 6 probe):

| Signal | Corrupted | Repaired |
| --- | :---: | :---: |
| Agent accuracy (nội dung) | 0.75 | 1.0 |
| Silent failures / trích sai bài | 8 / 7 | 0 / 0 |
| Bài thiếu / dòng trùng trong collection | 5 / 3 | 0 / 0 |
| Vector thay đổi (cosine thấp nhất) | 12 (0.825) | 0 (1.0) |
| Top-1 trùng baseline / thứ hạng giống hệt | 56% / 0% | 100% / 100% |

### Kết luận từ số liệu

1. Drop 20% bài mới + nhân bản + xóa summary → GX fail 2 expectation (unique `paper_id`, độ dài `summary`) → Hit Rate 1.0 → 0.6, F1 → 0.753, và agent có 8 silent failure.
2. Repair đọc lại từ raw snapshot, chạy lại cleaning → GX pass 6/6 → Hit Rate, F1, judge về đúng baseline; vector và thứ hạng trùng tuyệt đối, câu trả lời agent giống baseline từng ký tự.

**Corruption ảnh hưởng rõ nhất:** `drop_latest_records` — 4/10 bài đích của testset bị xóa. Nguy hiểm nhất là nó không làm agent im lặng: semantic search trả về bài gần trùng và agent trả lời trôi chảy, trích nguồn sai. `stale_date` cũng nguy hiểm vì agent trả sai ngày trên đúng bài mà không có tín hiệu nào.

**Khác với kỳ vọng:**
- Freshness SLA không bắt được `stale_date`: 3 bài bị lùi ngày, cộng bài `…805` vốn đã cũ từ baseline và bị `duplicate_rows` nhân thành 2 dòng → 5/22 = 22.7% < 25%. Kiểm tra bằng `build_freshness_report` trên DataFrame corrupted. Đây là giới hạn của SLA dạng tỷ lệ: sai lệch nhỏ nhưng nhắm đúng bài vẫn lọt qua. Cần báo Điệp (owner freshness) để cân nhắc ngưỡng hoặc cảnh báo theo từng bài.
- `inject_noise` và `duplicate_rows` gần như không ảnh hưởng câu trả lời: noise không rơi vào câu đầu summary, còn bản nhân bản có cùng nội dung. Chúng chỉ lộ ra qua GX (duplicate) chứ không qua metric agent.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** giữ raw snapshot bất biến làm "nguồn sự thật" khiến repair trở nên đơn giản và idempotent — chạy 2 lần cho kết quả giống hệt.
2. **Observability:** mỗi tín hiệu chỉ bắt được một lớp lỗi. GX bắt duplicate và summary rỗng nhưng không bắt ngày bị lùi; freshness theo tỷ lệ bỏ lọt khi ít bài bị ảnh hưởng. Cần nhiều tín hiệu chồng nhau.
3. **Ảnh hưởng tới RAG agent:** dữ liệu hỏng không làm agent báo lỗi mà làm nó trả lời tự tin từ tài liệu sai. Cần kiểm tra **nguồn** chứ không chỉ nội dung câu trả lời.

### Nếu có thêm thời gian

Thêm một expectation/monitor ở tầng retrieval: với mỗi câu hỏi có tiêu đề, cảnh báo khi `lookup_paper` trượt mà phải rơi xuống semantic search (trên corrupted: 7/16 câu, trên baseline: 0). Đo bằng số cảnh báo trên từng collection; kỳ vọng tín hiệu này bắt được `drop_latest` và `truncate_title` sớm hơn metric cuối. Đồng thời chạy lại toàn bộ với một LLM thật để kiểm chứng tiêu chí "sai nguồn".

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Tiến Tuân
**Ngày xác nhận:** 2026-09-25
