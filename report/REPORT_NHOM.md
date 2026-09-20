# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** Transformer
**Thành viên:** Trần Kim Phương, Trần Gia Thành, Nguyễn Minh Thái
**Ngày:** 20 Tháng 9, 2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Thương mại điện tử, cụ thể chính sách đổi trả hàng, bảo hành, chính sách bán hàng

**Tại sao nhóm chọn chủ đề này?**
> Chủ đề mang tính thực tế, có thể scrape được data từ các trang thương mại điện tử tại Việt Nam

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | Chính sách nhà bán hàng | https://pyloherb.com/2021/05/26/chinh-sach-nha-ban-hang/ | 2026-09-20 / `not-stated` | 3.728 | `doc_id`, `audience: seller`, `category: chinh-sach-ban-hang`, `source_url`, `retrieved_at`, `document_version` |
| 2 | Chính sách đổi trả hàng hóa — HiClean | https://hiclean.com.vn/ho-tro-khach-hang/chinh-sach-doi-tra-hang-hoa | 2026-09-20 / `not-stated` | 7.030 | `doc_id`, `audience: buyer`, `category: doi-tra-hang`, `source_url`, `retrieved_at`, `document_version` |
| 3 | Quy định đổi trả hàng và hoàn tiền — SmartHomeKit | https://smarthomekit.vn/quy-dinh-doi-tra-hang-va-hoan-tien/ | 2026-09-20 / `not-stated` | 4.857 | `doc_id`, `audience: buyer`, `category: doi-tra-hang`, `source_url`, `retrieved_at`, `document_version` |
| 4 | Chính sách đổi trả và hoàn tiền — Thế Giới Nệm | https://thegioinem.com/chinh-sach-doi-tra-va-hoan-tien | 2026-09-20 / `not-stated` | 8.266 | `doc_id`, `audience: buyer`, `category: doi-tra-hang`, `source_url`, `retrieved_at`, `document_version` |
| 5 | Chính sách kiểm hàng và đổi trả hàng hóa — XTrend | https://xtrend.vn/chinh-sach-doi-tra-hang/ | 2026-09-20 / `not-stated` | 4.397 | `doc_id`, `audience: buyer`, `category: doi-tra-hang`, `source_url`, `retrieved_at`, `document_version` |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [ x ] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [ x ] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `doc_id` | Chuỗi, duy nhất | `chinh-sach-ban-hang-seller-pyloherb` | Định danh tài liệu, giúp đối chiếu chunk với tài liệu gốc và tránh nhầm lẫn giữa các tài liệu có tiêu đề giống nhau. |
| `title` | Chuỗi | `Chính sách nhà bán hàng` | Cung cấp ngữ cảnh ngắn gọn cho chunk và hỗ trợ tìm kiếm theo tên hoặc chủ đề tài liệu. |
| `source_url` | Chuỗi (URL) | `https://pyloherb.com/2021/05/26/chinh-sach-nha-ban-hang/` | Cho phép truy vết, kiểm chứng câu trả lời và mở lại nguồn công khai ban đầu. |
| `retrieved_at` | Chuỗi ngày (`YYYY-MM-DD`) | `2026-09-20` | Cho biết thời điểm thu thập để đánh giá độ mới của dữ liệu hoặc ưu tiên bản được lấy gần nhất. |
| `document_version` | Chuỗi | `not-stated` | Hỗ trợ phân biệt các phiên bản chính sách; `not-stated` thể hiện minh bạch rằng nguồn không công bố phiên bản. |
| `audience` | Chuỗi phân loại | `buyer`, `seller` | Cho phép lọc theo đối tượng áp dụng, đặc biệt tránh trả chính sách dành cho người mua khi truy vấn hỏi về người bán. |
| `category` | Chuỗi phân loại | `doi-tra-hang`, `chinh-sach-ban-hang` | Thu hẹp phạm vi tìm kiếm theo loại chính sách, giảm các chunk không liên quan trong kết quả top-k. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Nhóm chạy `ChunkingStrategyComparator().compare()` với `chunk_size=200` (giá trị mặc định) trên ba tài liệu. Khối YAML frontmatter được loại bỏ trước khi đo để số liệu chỉ phản ánh phần nội dung. Với `FixedSizeChunker`, comparator tự đặt `overlap=50`; `SentenceChunker` dùng mặc định 3 câu/chunk.

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| Chính sách nhà bán hàng — PyLoHerb | FixedSizeChunker (`fixed_size`) | 23 | 198,26 ký tự | Thấp: kích thước đồng đều và overlap giúp nối tiếp ngữ cảnh, nhưng nhiều ranh giới cắt giữa từ, câu hoặc bảng. |
| Chính sách nhà bán hàng — PyLoHerb | SentenceChunker (`by_sentences`) | 9 | 381,33 ký tự | Trung bình: giữ trọn câu, nhưng bullet/bảng Markdown không có dấu kết câu làm một số chunk rất dài (tối đa 1.143 ký tự) và trộn nhiều mục. |
| Chính sách nhà bán hàng — PyLoHerb | RecursiveChunker (`recursive`) | 24 | 144,17 ký tự | Khá: ưu tiên ranh giới đoạn và dòng nên nội dung dễ đọc hơn, nhưng có thể tách heading thành chunk ngắn khỏi phần nội dung liên quan. |
| Chính sách đổi trả hàng hóa — HiClean | FixedSizeChunker (`fixed_size`) | 45 | 199,31 ký tự | Thấp: overlap hạn chế mất thông tin ở biên, song điều kiện và câu dài vẫn bị cắt giữa chừng. |
| Chính sách đổi trả hàng hóa — HiClean | SentenceChunker (`by_sentences`) | 18 | 372,22 ký tự | Khá: các câu mô tả điều kiện được giữ nguyên; tuy nhiên các danh sách bullet thường bị gom thành chunk lớn, làm giảm độ tập trung khi truy xuất. |
| Chính sách đổi trả hàng hóa — HiClean | RecursiveChunker (`recursive`) | 46 | 147,15 ký tự | Tốt: phần lớn điều kiện/bullet được tách thành đơn vị hoàn chỉnh và vẫn nằm dưới ngưỡng 200 ký tự; đôi lúc heading chưa đi cùng chunk kế tiếp. |
| Quy định đổi trả hàng và hoàn tiền — SmartHomeKit | FixedSizeChunker (`fixed_size`) | 31 | 196,55 ký tự | Thấp: tạo chunk ổn định nhưng cắt ngang từ, câu và chuỗi điều kiện, dù có overlap 50 ký tự. |
| Quy định đổi trả hàng và hoàn tiền — SmartHomeKit | SentenceChunker (`by_sentences`) | 14 | 325,50 ký tự | Khá: giữ được câu và quy trình hoàn chỉnh hơn fixed-size, nhưng độ dài biến động và có chunk tới 554 ký tự. |
| Quy định đổi trả hàng và hoàn tiền — SmartHomeKit | RecursiveChunker (`recursive`) | 29 | 158,38 ký tự | Tốt nhất trong ba baseline: đa số bullet/đoạn được bảo toàn, kích thước tương đối gọn; vẫn có rủi ro heading đứng riêng và làm mất nhãn mục. |

**Nhận xét:** `FixedSizeChunker` cho kích thước dễ dự đoán nhưng có độ mạch lạc thấp nhất vì cắt theo ký tự. `SentenceChunker` bảo toàn câu tốt hơn, song không phù hợp hoàn toàn với tài liệu chính sách nhiều heading, bullet và bảng Markdown nên sinh chunk quá dài. `RecursiveChunker` cân bằng tốt nhất giữa kích thước và tính mạch lạc trên ba tài liệu, nhưng chưa bảo đảm tiêu đề mục luôn đi cùng nội dung.

Theo yêu cầu riêng của biến thể K4-L3B, nhóm vẫn cần **ít nhất một thành viên thử chiến lược theo heading/section**. Heading không nên trở thành một chunk đứng riêng; nên tạo mỗi section gồm **tiêu đề + nội dung** thành một chunk, và nếu section quá dài thì chia tiếp bằng recursive rồi gắn lại tiêu đề vào từng chunk con để bảo toàn ngữ cảnh.

### Chiến lược của từng thành viên

> Mỗi thành viên điền một khối dưới đây (copy thêm nếu nhóm có nhiều hơn 3 người).

**Thành viên 1 — Nguyễn Minh Thái**
- **Loại chiến lược:** FixedSizeChunker (`chunk_size=500`, `overlap=50`)
- **Mô tả & lý do chọn cho chủ đề này:** Chiến lược chia văn bản thành các đoạn có kích thước cố định và lặp lại 50 ký tự giữa hai chunk liên tiếp. Đây là mốc đối chứng đơn giản, có chi phí và số lượng chunk dễ dự đoán; overlap giúp giảm nguy cơ mất thông tin ở biên, dù vẫn có thể cắt ngang câu, điều kiện hoặc bảng Markdown.
- **Code snippet:** Không có — sử dụng `FixedSizeChunker` trong `src/chunking.py`.

**Thành viên 2 — Trần Gia Thành**
- **Loại chiến lược:** RecursiveChunker (`chunk_size=500`)
- **Mô tả & lý do chọn:** Chiến lược lần lượt ưu tiên tách theo đoạn, dòng, câu rồi khoảng trắng, sau đó gom các mảnh nhỏ đến gần giới hạn kích thước. Cách này phù hợp với chính sách thương mại điện tử vì giữ được phần lớn bullet, đoạn giải thích và điều kiện hoàn chỉnh, đồng thời tránh các chunk quá dài.
- **Code snippet:** Không có — sử dụng `RecursiveChunker` trong `src/chunking.py`.

**Thành viên 3 — Trần Kim Phương**
- **Loại chiến lược:** Custom Heading/Section Chunker (`chunk_size=500`, recursive fallback)
- **Mô tả & lý do chọn:** Các tài liệu chính sách đã được tổ chức thành các mục `##`, vì vậy mỗi heading cùng nội dung của section tương ứng là một đơn vị ngữ nghĩa tự nhiên. Nếu section vượt quá 500 ký tự, nội dung được chia tiếp bằng `RecursiveChunker` và heading được gắn lại vào từng chunk con; nhờ đó kết quả truy xuất luôn giữ được tên điều khoản và đáp ứng yêu cầu heading/section chunking của K4-L3B.
- **Code snippet (custom):**

```python
import re

from src.chunking import RecursiveChunker


class HeadingChunker:
    def __init__(self, chunk_size: int = 500) -> None:
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []

        # Chỉ tách tại heading cấp 2; các heading cấp 3 và nội dung bên
        # dưới vẫn thuộc cùng section.
        headings = list(re.finditer(r"(?m)^##(?!#)\s+.+$", text))
        if not headings:
            return RecursiveChunker(chunk_size=self.chunk_size).chunk(text)

        chunks: list[str] = []
        preamble = text[: headings[0].start()].strip()
        if preamble:
            chunks.extend(
                RecursiveChunker(chunk_size=self.chunk_size).chunk(preamble)
            )

        for index, match in enumerate(headings):
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            heading = match.group().strip()
            content = text[match.end() : end].strip()
            section = f"{heading}\n\n{content}" if content else heading

            if len(section) <= self.chunk_size:
                chunks.append(section)
                continue

            # Chừa chỗ để gắn heading vào mọi chunk con.
            child_size = max(1, self.chunk_size - len(heading) - 2)
            child_chunks = RecursiveChunker(chunk_size=child_size).chunk(content)
            chunks.extend(f"{heading}\n\n{part}" for part in child_chunks)

        return chunks
```

### So Sánh Giữa Các Thành Viên

Nhóm chạy cùng 5 câu hỏi đánh giá trên đúng 5 tài liệu trong Data Inventory, dùng mô hình local `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` để lấy top-3. Các chunk truy xuất được sau đó được truyền qua `KnowledgeBaseAgent` đến LLM thực tế `openai/gpt-4.1-mini`; câu trả lời được đối chiếu thủ công với gold answer. Mỗi câu được 2 điểm khi chunk đáp án ở top-1 và agent trả lời đúng, 1 điểm khi chunk ở top-2/3 hoặc câu trả lời còn thiếu chi tiết, và 0 điểm khi top-3 không chứa đủ bằng chứng. Cả ba chiến lược đều dùng `chunk_size=500`; riêng FixedSize có `overlap=50`, còn Heading/Section dùng recursive fallback và gắn lại heading vào từng chunk con.

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Nguyễn Minh Thái | FixedSizeChunker | 6/10 | Kích thước ổn định; overlap cho thông tin ở ranh giới thêm cơ hội xuất hiện trong top-3; đưa chunk chứa đáp án lên top-1 ở câu HiClean và Smart HomeKit. | Có thể cắt ngang từ, câu, bảng hoặc điều kiện; câu PyLoHerb và Tatana chỉ đạt top-2, còn câu XTREND trả về đúng tài liệu nhưng sai đoạn. |
| Trần Gia Thành | RecursiveChunker | 5/10 | Chunk mạch lạc, ít trộn các phần không liên quan; tên công ty trong query giúp câu Smart HomeKit đưa đúng chunk COD lên top-1. | Không có overlap và không giữ heading cho mọi chunk con; các câu PyLoHerb, HiClean và Tatana chỉ đạt top-3, còn câu XTREND không tìm thấy chunk đáp án. |
| Trần Kim Phương | Heading/Section Chunker | 4/10 | Giữ tên mục trong từng chunk, giúp câu Tatana đưa đúng section lên top-1 và kết quả dễ truy vết về điều khoản. | Sinh nhiều chunk nhất (78 chunk so với 62 của Fixed-size và 66 của Recursive); các chunk cùng lặp heading/tên chủ đề cạnh tranh vị trí top-3, làm mất chunk đáp án ở các câu HiClean, COD và XTREND. |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> Trên bộ 5 câu hỏi hiện tại, `FixedSizeChunker(chunk_size=500, overlap=50)` đạt điểm cao nhất (6/10), sát với `RecursiveChunker` (5/10), vì overlap làm giảm rủi ro đáp án bị mất tại biên chunk. Heading/Section tạo chunk dễ giải thích và thắng ở các câu PyLoHerb, Tatana có cấu trúc mục rõ ràng, nhưng việc lặp heading làm nhiều chunk cùng chủ đề cạnh tranh vị trí top-3 nên tổng điểm chỉ đạt 4/10. Kết quả cho thấy chunk mạch lạc chưa tự động bảo đảm thứ hạng truy xuất tốt: kích thước, overlap và cách diễn đạt query vẫn ảnh hưởng trực tiếp đến top-k.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Đối với người bán hoặc đại lý của PyLoHerb, chi phí vận chuyển và bốc dỡ được hỗ trợ như thế nào? **Dùng `metadata_filter={"audience": "seller"}`.** | PyLoHerb hỗ trợ vận chuyển đơn hàng từ công ty đến đối tác bán hàng; chi phí bốc dỡ mỗi bên chịu một đầu. | `chinh-sach-ban-hang-seller-pyloherb` — mục **III. Hỗ trợ đại lý**. |
| 2 | Theo chính sách HiClean, khách hàng đổi hàng từ ngày 04 đến ngày 07 phải chịu mức phí bao nhiêu? | Khách hàng phải chịu 20% phí đổi hàng, cùng phí vận chuyển, lắp đặt và phần chênh lệch giá trị hàng hóa nếu có. | `doi-tra-hang-hiclean` — mục **Các trường hợp được đổi hàng**. |
| 3 | Với đơn hàng COD tại Smart HomeKit, người mua phải cung cấp thông tin gì để nhận tiền hoàn trả? | Người mua phải cung cấp thông tin tài khoản ngân hàng để nhận tiền hoàn trả. | `doi-tra-hang-smarthomekit` — **II. Quy định hoàn tiền → Hoàn tiền cho hàng trả lại**. |
| 4 | Theo chính sách 102 ngày ngủ thử Tatana của Thế Giới Nệm, thời gian xử lý hoàn tiền là bao lâu? | Trong vòng 14 ngày làm việc kể từ khi Thế Giới Nệm nhận lại sản phẩm và xác nhận sản phẩm đạt điều kiện. | `doi-tra-hang-thegioinem` — **Chính sách 102 ngày ngủ thử sản phẩm Tatana → Điều kiện áp dụng/Quy trình đổi trả**. |
| 5 | Khách mua hàng online tại XTREND được yêu cầu đổi trả trong thời gian bao lâu? | Trong vòng 07 ngày kể từ khi nhận hàng. | `doi-tra-hang-xtrend` — **Chính sách đổi/trả hàng hóa → Điều kiện đổi/trả hàng**. |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | PyLoHerb hỗ trợ vận chuyển và bốc dỡ cho người bán/đại lý thế nào? | Heading/Section Chunker | Có — top-1 | Khi lọc `audience=seller`, Fixed-size xếp chunk đáp án ở top-2, Recursive ở top-3, còn Heading/Section ở top-1. |
| 2 | Theo HiClean, đổi hàng từ ngày 04 đến ngày 07 chịu mức phí bao nhiêu? | FixedSizeChunker | Có — top-1 | Fixed-size và Recursive trả lời đúng; Heading/Section thiếu chunk đáp án nên agent trả lời sai rằng từ ngày 04 không được hỗ trợ. |
| 3 | Đơn COD tại Smart HomeKit cần thông tin gì để nhận hoàn tiền? | FixedSizeChunker và RecursiveChunker | Có — top-1 | Hai chiến lược tốt nhất trả lời đúng là tài khoản ngân hàng; Heading/Section thiếu bằng chứng nên agent nói không đủ thông tin. |
| 4 | Hoàn tiền cho nệm Tatana của Thế Giới Nệm mất bao lâu? | Heading/Section Chunker | Có — top-1 | Heading/Section và Recursive trả lời đúng; Fixed-size nêu đúng 14 ngày nhưng gắn nhầm mốc bắt đầu với việc xác nhận bài chia sẻ. |
| 5 | Thời hạn đổi trả hàng online tại XTREND? | Không có chiến lược đạt | Không | Cả ba trả về chunk đúng tài liệu hoặc đúng chủ đề nhưng sai section; agent đều nói không đủ thông tin về mốc 07 ngày. |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> Có, metadata filter cải thiện rõ kết quả ở câu 1 dù query đã nêu PyLoHerb. Khi không lọc, FixedSize và Recursive không đưa chunk chứa đáp án vào top-3 do các chunk về chi phí vận chuyển đổi/trả dành cho buyer xếp cao hơn; khi dùng `metadata_filter={"audience": "seller"}`, chunk đáp án lên lần lượt top-2 và top-3. Heading/Section đã tìm đúng ở top-1 ngay cả khi không lọc, nên filter không thay đổi thứ hạng của riêng chiến lược này. Như vậy filter vẫn giúp ngăn việc trộn chính sách buyer và seller, nhưng mức tác động phụ thuộc vào cách chunking.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
>
> - Chunk mạch lạc chưa chắc có điểm truy xuất cao nhất: FixedSize đạt 6/10 nhờ overlap 50 ký tự, Recursive đạt 5/10, còn Heading/Section đạt 4/10 dù các chunk dễ đọc và truy vết hơn.
> - Metadata filter có thể quan trọng ngay cả khi query đã nêu tên công ty. Với câu PyLoHerb, FixedSize và Recursive không tìm thấy chunk đáp án trong top-3 khi không lọc, nhưng sau khi lọc `audience=seller`, đáp án lần lượt lên top-2 và top-3.
> - Đúng tài liệu chưa đồng nghĩa với đúng bằng chứng: ở câu XTREND, cả ba chiến lược đều trả về chunk đúng tài liệu hoặc đúng chủ đề nhưng sai section, nên không chunk nào trong top-3 chứa mốc thời gian 07 ngày.

**Bài học rút ra khi so sánh trong nhóm:**
> Trên cùng một corpus và cùng mô hình embedding, cách đặt ranh giới chunk làm thay đổi rõ thứ hạng top-k. FixedSize hưởng lợi từ overlap nhưng có thể cắt ngang ý; Recursive tạo đoạn mạch lạc hơn nhưng mỗi thông tin chỉ có một cơ hội được truy xuất; Heading/Section giữ được tên điều khoản và thắng ở câu Tatana, song việc lặp heading khiến nhiều chunk cùng chủ đề cạnh tranh nhau. Vì vậy không có chiến lược tốt nhất cho mọi câu hỏi, và cần đánh giá trên nội dung thật sự chứa đáp án thay vì chỉ kiểm tra `doc_id`.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Nhóm sẽ thử chiến lược lai: tách theo heading trước, chia section dài bằng RecursiveChunker, gắn lại heading và thêm một overlap nhỏ giữa các chunk con. Nhóm cũng sẽ chuẩn hóa tên công ty, loại chính sách và `audience` trong metadata, đồng thời mở rộng benchmark với nhiều cách diễn đạt cho cùng một ý để tránh kết luận phụ thuộc vào một câu query. Cuối cùng, nhóm sẽ lưu tự động top-3, nội dung chunk và kết quả A/B có/không filter để việc chấm điểm và phân tích lỗi có thể tái lập.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 15 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 9 / 10 |
| Thuyết trình (Demo) | 5 / 5 |
| **Tổng phần nhóm** | ** 39 / 40** |