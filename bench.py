from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Callable, TextIO

from dotenv import load_dotenv

from src.chunking import (
    ChunkingStrategyComparator,
    FixedSizeChunker,
    RecursiveChunker,
    SentenceChunker,
)
from src.embeddings import GeminiEmbedder, LocalEmbedder, MockEmbedder, OpenAIEmbedder
from src.models import Document
from src.store import EmbeddingStore


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "ecommerce"
RESULT_PATH = ROOT / "ket_qua_benchmark.txt"

# Make Vietnamese benchmark output readable when launched from a legacy Windows console.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BENCHMARKS = [
    {
        "query": "Khách mua online tại LUG có bao nhiêu ngày để đổi trả và điều kiện cơ bản là gì?",
        "gold_answer": (
            "Trong 07 ngày kể từ ngày nhận hàng; có hóa đơn hoặc thông tin mua hàng "
            "trên hệ thống bảo hành điện tử; sản phẩm còn nguyên vẹn và chưa qua sử dụng."
        ),
        "gold_doc_id": "chinh-sach-doi-tra-hang",
        "evidence": "Trong thời gian 07 ngày kể từ ngày nhận hàng",
        "metadata_filter": None,
    },
    {
        "query": (
            "Sản phẩm Giày BQ được giảm giá từ 25% có được trả hàng "
            "hay chỉ được đổi màu hoặc size?"
        ),
        "gold_answer": (
            "Không. Sản phẩm ưu đãi từ 25% trở lên chỉ được đổi màu hoặc size khi còn hàng, "
            "không được hỗ trợ trả hàng."
        ),
        "gold_doc_id": "chinh-sach-doi-tra",
        "evidence": "Chỉ áp dụng đổi màu/size",
        "metadata_filter": None,
    },
    {
        "query": (
            "Khánh Vy Home hoàn tiền theo quy trình và thời gian nào nếu sản phẩm "
            "đổi mới cùng model vẫn bị lỗi kỹ thuật?"
        ),
        "gold_answer": (
            "Khách được hoàn tiền nếu sản phẩm đổi mới cùng loại, model và nhãn hiệu "
            "vẫn lỗi kỹ thuật. Khánh Vy Home hoàn trong 24–72 giờ sau khi nhận xác nhận "
            "của nhà sản xuất rằng lỗi không thể khắc phục."
        ),
        "gold_doc_id": "chinh-sach-doi-tra-va-hoan-tien",
        "evidence": "Thời gian hoàn tiền cho khách hàng sau 24h",
        "metadata_filter": {"category": "returns-policy"},
    },
    {
        "query": (
            "Khách phải chờ bao lâu để nhận lại sản phẩm sau bảo hành: lỗi nhẹ tại chỗ, "
            "sản phẩm thông thường và lỗi nặng gửi xưởng?"
        ),
        "gold_answer": (
            "Lỗi nhẹ: 15–20 phút; thông thường: 2–3 ngày, không tính Chủ nhật; "
            "lỗi nặng phải gửi xưởng: 7–10 ngày, không tính Chủ nhật."
        ),
        "gold_doc_id": "chinh-sach-bao-hanh-tron-doi",
        "evidence": "15 - 20 phút",
        "metadata_filter": {"category": "warranty-policy"},
    },
    {
        "query": (
            "Khi không đồng ý với quyết định xử lý yêu cầu trả hàng hoàn tiền, "
            "cần gửi phản hồi trong bao lâu?"
        ),
        "gold_answer": (
            "Người bán phải phản hồi trong vòng 02 ngày lịch kể từ ngày nhận thông báo "
            "của Shopee, trừ khi Shopee quy định thời hạn khác."
        ),
        "gold_doc_id": "shopee-nguoi-ban-tra-hang-hoan-tien",
        "evidence": "phản hồi trong vòng 02 ngày lịch",
        "metadata_filter": {"audience": "seller"},
    },
]


class CachedEmbedder:
    """Persistent hash cache, used only for paid OpenAI embeddings."""

    def __init__(self, embedder: Callable[[str], list[float]], cache_path: Path) -> None:
        self.embedder = embedder
        self.cache_path = cache_path
        self.cache: dict[str, list[float]] = {}
        if cache_path.exists():
            self.cache = json.loads(cache_path.read_text(encoding="utf-8"))

    def __call__(self, text: str) -> list[float]:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if key not in self.cache:
            self.cache[key] = self.embedder(text)
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(
                json.dumps(self.cache, ensure_ascii=False), encoding="utf-8"
            )
        return self.cache[key]


class TeeWriter:
    """Write benchmark output to both the terminal and a result file."""

    def __init__(self, *streams: TextIO) -> None:
        self.streams = streams

    def write(self, value: str) -> int:
        for stream in self.streams:
            stream.write(value)
        return len(value)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()


def parse_markdown(path: Path) -> tuple[dict[str, str], str]:
    """Return simple YAML frontmatter and body without requiring PyYAML."""
    text = path.read_text(encoding="utf-8").lstrip("\ufeff")
    if not text.startswith("---"):
        return {}, text.strip()

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text.strip()

    metadata: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"\'')
    return metadata, parts[2].strip()


def load_url_metadata() -> dict[str, dict[str, str]]:
    with (ROOT / "data" / "urls.csv").open(encoding="utf-8-sig", newline="") as handle:
        return {row["doc_id"]: row for row in csv.DictReader(handle)}


def iter_markdown_paths() -> list[Path]:
    """Return a stable list of every Markdown file in the benchmark corpus."""
    return sorted(path for path in DATA_DIR.rglob("*.md") if path.is_file())


def build_documents(chunker: object) -> list[Document]:
    references = load_url_metadata()
    documents: list[Document] = []
    for path in iter_markdown_paths():
        doc_id = path.stem
        frontmatter, body = parse_markdown(path)

        # CSV fields fill optional metadata; frontmatter remains authoritative.
        metadata = {**references.get(doc_id, {}), **frontmatter, "doc_id": doc_id}
        for index, chunk in enumerate(chunker.chunk(body)):
            documents.append(
                Document(
                    id=f"{doc_id}#{index}",
                    content=chunk,
                    metadata=dict(metadata),
                )
            )
    return documents


def build_embedder() -> tuple[str, Callable[[str], list[float]]]:
    provider = os.getenv("EMBEDDING_PROVIDER", "mock").strip().lower()
    if provider == "local":
        embedder = LocalEmbedder(os.getenv("LOCAL_EMBEDDING_MODEL") or None) if os.getenv(
            "LOCAL_EMBEDDING_MODEL"
        ) else LocalEmbedder()
        return f"local:{embedder.model_name}", embedder
    if provider == "openai":
        model = os.getenv("OPENAI_EMBEDDING_MODEL")
        embedder = OpenAIEmbedder(model) if model else OpenAIEmbedder()
        cached = CachedEmbedder(embedder, ROOT / ".cache" / "openai_embeddings.json")
        return f"openai:{embedder.model_name} (cached)", cached
    if provider == "gemini":
        model = os.getenv("GEMINI_EMBEDDING_MODEL")
        embedder = GeminiEmbedder(model) if model else GeminiEmbedder()
        return f"gemini:{embedder.model_name}", embedder
    if provider != "mock":
        raise ValueError(f"Unsupported EMBEDDING_PROVIDER={provider!r}")
    return "mock embeddings fallback (scores are not semantic)", MockEmbedder()


def compact(text: str, limit: int = 180) -> str:
    normalized = " ".join(text.split())
    return normalized if len(normalized) <= limit else normalized[: limit - 3] + "..."


def contains_evidence(result: dict, benchmark: dict) -> bool:
    return (
        result["metadata"].get("doc_id") == benchmark["gold_doc_id"]
        and benchmark["evidence"].casefold() in result["content"].casefold()
    )


def print_baseline() -> None:
    print("\n=== BASELINE (frontmatter removed, chunk_size=500) ===")
    comparator = ChunkingStrategyComparator()
    for doc_id in [
        "chinh-sach-doi-tra-hang",
        "chinh-sach-doi-tra",
        "shopee-nguoi-ban-tra-hang-hoan-tien",
    ]:
        _, body = parse_markdown(DATA_DIR / f"{doc_id}.md")
        comparison = comparator.compare(body, chunk_size=500)
        for strategy, values in comparison.items():
            print(
                f"{doc_id:43} {strategy:12} "
                f"count={values['count']:4} avg_length={values['avg_length']:.1f}"
            )


def run_benchmark() -> int:
    # Change only this line when benchmarking another member's strategy.
    chunker = FixedSizeChunker(chunk_size=800, overlap=80)
    # Alternatives: FixedSizeChunker(800, 80), SentenceChunker(4), RecursiveChunker(chunk_size=800)

    backend_name, embedder = build_embedder()
    documents = build_documents(chunker)
    store = EmbeddingStore(collection_name="ecommerce-benchmark", embedding_fn=embedder)
    store.add_documents(documents)

    print(f"Embedding backend: {backend_name}")
    print(f"Chunker: {type(chunker).__name__}")
    print(f"Documents: {len(iter_markdown_paths())}")
    print(f"Loaded chunks: {store.get_collection_size()}")

    hit_count = 0
    for number, benchmark in enumerate(BENCHMARKS, start=1):
        results = store.search_with_filter(
            benchmark["query"],
            top_k=3,
            metadata_filter=benchmark["metadata_filter"],
        )
        hit = any(contains_evidence(result, benchmark) for result in results)
        hit_count += int(hit)

        print(f"\nQ{number}: {benchmark['query']}")
        print(f"Filter: {benchmark['metadata_filter'] or '{}'}")
        print(f"Gold: {benchmark['gold_answer']}")
        for rank, result in enumerate(results, start=1):
            marker = " GOLD" if contains_evidence(result, benchmark) else ""
            print(
                f"  {rank}. score={result['score']:.4f} "
                f"doc_id={result['metadata'].get('doc_id')} chunk_id={result['id']}{marker}"
            )
            print(f"     {compact(result['content'])}")
        print(f"Top-3 evidence: {'YES' if hit else 'NO'}")

        # The filtered question is also run without a filter to demonstrate A/B impact.
        if benchmark["metadata_filter"]:
            unfiltered = store.search_with_filter(benchmark["query"], top_k=3)
            unfiltered_ids = [result["metadata"].get("doc_id") for result in unfiltered]
            unfiltered_hit = any(contains_evidence(result, benchmark) for result in unfiltered)
            print(
                "A/B without filter: "
                f"top3={unfiltered_ids}; evidence={'YES' if unfiltered_hit else 'NO'}"
            )

    print(f"\nEvidence hit@3: {hit_count}/{len(BENCHMARKS)}")
    print_baseline()
    return 0


def main() -> int:
    load_dotenv(ROOT / ".env")

    with RESULT_PATH.open("w", encoding="utf-8") as result_file:
        with redirect_stdout(TeeWriter(sys.stdout, result_file)):
            exit_code = run_benchmark()

    print(f"Saved benchmark results to: {RESULT_PATH.name}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
