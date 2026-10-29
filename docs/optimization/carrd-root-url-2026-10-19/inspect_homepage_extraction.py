"""Independent source inspection, never ingested as additional campaign material."""
import json
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent
REPO = ROOT.parents[2]
sys.path.insert(0, str(REPO / "backend"))
from app.ingestion.loaders.html_extract import extract_content

response = httpx.get("https://carrd.com/", follow_redirects=True, timeout=30)
response.raise_for_status()
(ROOT / "independent-homepage.html").write_text(response.text, encoding="utf-8")
soup = BeautifulSoup(response.text, "html.parser")
headers = [{"text":h.get_text(" ",strip=True), "parent":h.parent.name,
            "parent_id":h.parent.get("id"), "html":str(h)[:3000]} for h in soup.find_all("header")]
review = {"url":str(response.url), "headers":headers, "extracted":extract_content(response.text)[2]}
(ROOT / "independent-extraction-review.json").write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"headers":headers},ensure_ascii=False,indent=2))
