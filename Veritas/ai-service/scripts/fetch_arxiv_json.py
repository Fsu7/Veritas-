import json
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from import_papers import fetch_papers_from_arxiv, clean_papers

async def main():
    papers = await fetch_papers_from_arxiv('cs.AI', 100)
    cleaned = clean_papers(papers)
    output = Path(__file__).resolve().parent.parent / 'data' / 'papers' / 'arxiv_cs_ai_100.json'
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
    print(f'Saved {len(cleaned)} papers to {output}')

asyncio.run(main())
