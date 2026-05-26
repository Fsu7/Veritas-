import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb
from collections import defaultdict


def main():
    client = chromadb.PersistentClient(path="./data/vector_db")
    collection = client.get_collection("papers")
    results = collection.get(include=["metadatas", "documents"])

    papers = defaultdict(list)
    for i, meta in enumerate(results["metadatas"]):
        pid = meta.get("paper_id", "unknown")
        papers[pid].append(
            {
                "title": meta.get("title", ""),
                "year": meta.get("year", ""),
                "venue": meta.get("venue", ""),
                "chunk_index": meta.get("chunk_index", 0),
                "chunk_type": meta.get("chunk_type", ""),
                "document": results["documents"][i] if results["documents"] else "",
            }
        )

    print(f"ChromaDB papers collection 总计: {collection.count()} 条记录")
    print(f"去重后论文数: {len(papers)} 篇")
    print()

    for pid, chunks in sorted(papers.items()):
        p = chunks[0]
        print(f"paper_id: {pid}")
        print(f"  标题: {p['title']}")
        print(f"  年份: {p['year']}  类别: {p['venue']}")
        print(f"  分块数: {len(chunks)}")
        print(f"  摘要(首块): {p['document'][:200]}...")
        print()


if __name__ == "__main__":
    main()
