# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** [Tên sinh viên]
**Nhóm:** [Tên nhóm]
**Ngày:** [Ngày nộp]

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
Cosine similarity cao nghĩa là hai vector embedding có hướng gần nhau, cho thấy hai đoạn văn có nội dung hoặc ý nghĩa ngữ nghĩa gần nhau. Giá trị càng gần `1` thì mức tương đồng càng cao; gần `0` thường biểu thị ít liên quan và gần `-1` biểu thị hướng đối lập.

**Ví dụ có độ tương tự CAO:**
- Câu A: Cửa hàng sẽ hoàn lại tiền nếu sản phẩm bị lỗi.
- Câu B: Khách hàng được nhận lại khoản thanh toán khi hàng hóa có khiếm khuyết.
- Tại sao tương đồng: Hai câu dùng từ vựng khác nhau nhưng cùng diễn đạt việc hoàn tiền cho khách hàng khi sản phẩm có lỗi.

**Ví dụ có độ tương tự THẤP:**
- Câu A: Người mua có thể đổi sản phẩm trong vòng bảy ngày.
- Câu B: Mưa lớn dự kiến xuất hiện ở miền Trung vào chiều mai.
- Tại sao khác: Một câu nói về chính sách đổi hàng, câu còn lại nói về dự báo thời tiết nên gần như không có quan hệ ngữ nghĩa.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
Cosine tập trung vào góc giữa các vector nên ít bị ảnh hưởng bởi độ lớn vector, vốn có thể thay đổi theo độ dài hoặc đặc điểm của văn bản; nhờ đó nó phù hợp để so sánh hướng ngữ nghĩa. Khi embedding đã được chuẩn hóa về độ dài `1`, dot product chính là cosine similarity và thứ hạng theo khoảng cách Euclid cũng tương đương, nhưng dot product/cosine tính trực tiếp và thuận tiện hơn.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
Số chunk là `ceil((10.000 - 50) / (500 - 50)) = ceil(9.950 / 450) = ceil(22,11...) = 23`.

**Đáp án:** 23 chunks. Kiểm tra bằng `FixedSizeChunker` cũng trả về `23`.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
Khi overlap tăng lên `100`, số chunk là `ceil((10.000 - 100) / (500 - 100)) = ceil(9.900 / 400) = 25`, tăng từ 23 lên 25; kết quả này cũng khớp với `FixedSizeChunker`. Overlap lớn hơn giúp giữ ngữ cảnh tại ranh giới chunk và giảm nguy cơ một ý quan trọng bị cắt đôi, nhưng làm tăng số chunk, dung lượng embedding và chi phí truy xuất.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
Tôi dùng regex `(?<=[.!?])(?:[ \t]+|\r?\n+)` để tách tại khoảng trắng ngay sau dấu kết thúc câu, nhờ lookbehind nên các dấu `.`, `!`, `?` vẫn được giữ lại. Các câu được chuẩn hóa khoảng trắng rồi gom theo `max_sentences_per_chunk`; text rỗng trả về danh sách rỗng. Cách đơn giản này chưa phân biệt được chữ viết tắt như `TS.`, `v.v.` và số thập phân, nên các trường hợp đó có thể bị cắt sai.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
Thuật toán thử separator từ ranh giới lớn đến nhỏ; mảnh vượt `chunk_size` được đệ quy với các separator còn lại, sau đó các mảnh nhỏ liền kề được gom lại đến sát giới hạn. Ba base case là text rỗng, text đã không vượt kích thước, và hết separator thì cắt cứng theo `chunk_size`; separator rỗng cũng chuyển sang nhánh cắt cứng này.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
Mỗi `Document` được chuẩn hóa thành record in-memory gồm `id`, nội dung, bản sao metadata và embedding; nếu metadata thiếu `doc_id`, giá trị này được suy ra từ tên file trước dấu `#` của chunk. Khi tìm kiếm, query chỉ được embed một lần, điểm tương tự được tính bằng dot product với từng record rồi sắp xếp giảm dần; vector embedding không được đưa vào kết quả trả về.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
`search_with_filter` lọc metadata trước khi tính similarity và chọn top-k, tránh để tài liệu sai metadata chiếm hết k vị trí. `delete_document` loại toàn bộ chunk có `metadata['doc_id']` khớp tài liệu gốc và trả `True` khi có ít nhất một chunk bị xóa, ngược lại trả `False`.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
Agent truy xuất top-k chunk, đánh số từng đoạn `[1]`, `[2]`, ... kèm `source_url`, đường dẫn nguồn hoặc `doc_id`, rồi đưa chúng vào prompt cùng câu hỏi. Prompt yêu cầu chỉ sử dụng ngữ cảnh, trích dẫn số nguồn và nói rõ khi dữ liệu không đủ; nếu store không trả kết quả thì agent trả thông báo ngay mà không gọi LLM.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
$ python -m unittest -v tests.test_solution
...
Ran 42 tests in 0.005s

OK
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

**Embedding backend sử dụng:** `LocalEmbedder` với model `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. Các điểm bên dưới được đo bằng embedding semantic đã chuẩn hóa (`||v|| = 1`), không sử dụng `MockEmbedder`; cấu hình khi đo là `EMBEDDING_PROVIDER=local`.

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Khách hàng có thể trả lại sản phẩm bị lỗi để nhận lại tiền. | Người mua được hoàn tiền khi hàng hóa có khiếm khuyết. | Cao | 0.701 | Có |
| 2 | Đơn hàng phải được gửi đi trong vòng hai ngày. | Người bán cần bàn giao kiện hàng cho đơn vị vận chuyển không quá 48 giờ. | Cao | 0.569 | Có |
| 3 | Sản phẩm được bảo hành miễn phí trong một năm. | Dự báo ngày mai trời có mưa lớn. | Thấp | 0.015 | Có |
| 4 | Tôi không muốn hoàn tiền cho khách hàng. | Khách hàng sẽ được hoàn tiền đầy đủ. | Thấp | 0.348 | Có |
| 5 | Cửa hàng bảo hành miễn phí lỗi kỹ thuật. | Người bán bị khóa tài khoản vì đăng sản phẩm cấm. | Thấp | 0.311 | Có |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
Cặp 4 bất ngờ nhất vì hai câu trái nhau về ý định hoàn tiền nhưng vẫn đạt `0.348`, cao hơn đáng kể so với cặp hoàn toàn khác chủ đề. Điều này cho thấy embedding nhận ra rất tốt chủ đề chung qua các khái niệm “khách hàng” và “hoàn tiền”, nhưng không phải lúc nào cũng biểu diễn chính xác phép phủ định hoặc quan hệ logic. Trong bảng này, tôi quy ước điểm từ `0.5` trở lên là tương đồng cao để đối chiếu dự đoán một cách nhất quán.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Đối với người bán hoặc đại lý của PyLoHerb, chi phí vận chuyển và bốc dỡ được hỗ trợ như thế nào? Dùng `metadata_filter={"audience": "seller"}`. | Top-1 chưa chứa đủ bằng chứng; chunk đáp án ở hạng 3, thuộc mục **III. Hỗ trợ đại lý**. | 1 / 2 (hạng 3) | Không ở top-1; có trong top-3 | PyLoHerb hỗ trợ vận chuyển từ công ty đến đối tác bán hàng; chi phí bốc dỡ mỗi bên chịu một đầu. |
| 2 | Theo chính sách HiClean, khách hàng đổi hàng từ ngày 04 đến ngày 07 phải chịu mức phí bao nhiêu? | Top-1 chưa phải chunk đáp án; chunk nêu mức phí nằm ở hạng 3. | 1 / 2 (hạng 3) | Không ở top-1; có trong top-3 | Khách hàng chịu 20% phí đổi hàng, phí vận chuyển, lắp đặt và phần chênh lệch giá trị hàng hóa nếu có. |
| 3 | Với đơn hàng COD tại Smart HomeKit, người mua phải cung cấp thông tin gì để nhận tiền hoàn trả? | Chunk thuộc phần **II. Quy định hoàn tiền**, nêu yêu cầu cung cấp thông tin tài khoản ngân hàng. | 2 / 2 (hạng 1) | Có | Người mua phải cung cấp thông tin tài khoản ngân hàng để nhận tiền hoàn trả. |
| 4 | Theo chính sách 102 ngày ngủ thử Tatana của Thế Giới Nệm, thời gian xử lý hoàn tiền là bao lâu? | Top-1 chưa phải chunk đáp án; chunk có mốc 14 ngày làm việc nằm ở hạng 3. | 1 / 2 (hạng 3) | Không ở top-1; có trong top-3 | Hoàn tiền trong vòng 14 ngày làm việc kể từ khi Thế Giới Nệm nhận lại sản phẩm và xác nhận sản phẩm đạt điều kiện. |
| 5 | Khách mua hàng online tại XTREND được yêu cầu đổi trả trong thời gian bao lâu? | Kết quả trả về đúng tài liệu/chủ đề nhưng sai mục, không chứa mốc 07 ngày. | 0 / 2 | Không | Agent cho biết ngữ cảnh truy xuất chưa đủ để xác định thời hạn đổi trả. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 4 / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Tôi nhận ra chunk mạch lạc chưa chắc có thứ hạng truy xuất tốt nhất: chiến lược Fixed-size của bạn Nguyễn Minh Thái đạt 6/10 nhờ overlap 50 ký tự, cao hơn Recursive của tôi 1 điểm. Từ chiến lược Heading/Section của bạn Trần Kim Phương, tôi học được lợi ích của việc giữ tên điều khoản trong chunk, nhưng cũng thấy rằng lặp heading quá nhiều có thể khiến các chunk cùng chủ đề cạnh tranh nhau; lần sau tôi sẽ thử kết hợp heading, recursive fallback và một overlap nhỏ.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 5 / 10 |
| **Tổng phần cá nhân** | **55 / 60** |
