import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

BASE = "https://www.shl.com"
LIST_URL = BASE + "/products/product-catalog/?start={start}&type=1"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "catalog.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
DETAIL_WORKERS = 8


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return normalize(" ".join(self.parts))


def fetch(url: str, timeout: int = 20) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", "ignore")


def strip_tags(html: str) -> str:
    parser = TextParser()
    parser.feed(html)
    return parser.text()


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(text)).strip()


def parse_bool_cell(cell_html: str) -> bool:
    return "-yes" in cell_html


def parse_list_page(html: str) -> list[dict]:
    tables = re.findall(r"<table[\s\S]*?</table>", html, flags=re.I)
    individual = next((table for table in tables if "Individual Test Solutions" in table), "")
    rows = re.findall(r"<tr[^>]*data-(?:course|entity)-id=[\s\S]*?</tr>", individual, flags=re.I)
    items = []
    for row in rows:
        link = re.search(r'<a\s+href="([^"]+)">([\s\S]*?)</a>', row, flags=re.I)
        if not link:
            continue
        cells = re.findall(r"<td[^>]*>([\s\S]*?)</td>", row, flags=re.I)
        test_types = re.findall(r'product-catalogue__key[^>]*>\s*([A-Z])\s*<', row)
        href = urljoin(BASE, link.group(1))
        items.append(
            {
                "name": strip_tags(link.group(2)),
                "url": href,
                "test_type": " ".join(test_types),
                "remote_testing": parse_bool_cell(cells[1]) if len(cells) > 1 else None,
                "adaptive_irt": parse_bool_cell(cells[2]) if len(cells) > 2 else None,
            }
        )
    return items


def field_after(label: str, text: str, stops: list[str]) -> str:
    pattern = re.escape(label) + r"\s*(.*?)\s*(?:" + "|".join(re.escape(stop) for stop in stops) + r"|$)"
    match = re.search(pattern, text, flags=re.I)
    return normalize(match.group(1)) if match else ""


def parse_detail(html: str) -> dict:
    main_text = strip_tags(html)
    stops = ["Job levels", "Languages", "Assessment length", "Test Type", "Remote Testing", "Downloads", "Accelerate Your Talent Strategy"]
    description = field_after("Description", main_text, stops)
    job_levels = split_csv(field_after("Job levels", main_text, ["Languages", "Assessment length", "Test Type", "Downloads"]))
    languages = split_csv(field_after("Languages", main_text, ["Assessment length", "Test Type", "Downloads"]))
    minutes = None
    minutes_match = re.search(r"Approximate Completion Time in minutes\s*=\s*(\d+)", main_text, flags=re.I)
    if minutes_match:
        minutes = int(minutes_match.group(1))
    test_match = re.search(r"Test Type:\s*([A-Z ]+)", main_text)
    return {
        "description": description,
        "job_levels": job_levels,
        "languages": languages,
        "assessment_length_minutes": minutes,
        "detail_test_type": normalize(test_match.group(1)) if test_match else "",
    }


def split_csv(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def scrape() -> list[dict]:
    seen: dict[str, dict] = {}
    empty_pages = 0
    for start in range(0, 600, 12):
        html = fetch(LIST_URL.format(start=start))
        page_items = parse_list_page(html)
        new_count = 0
        for item in page_items:
            if item["url"] not in seen:
                seen[item["url"]] = item
                new_count += 1
        print(f"list start={start}: {len(page_items)} items, {new_count} new", flush=True)
        empty_pages = empty_pages + 1 if new_count == 0 else 0
        if empty_pages >= 2:
            break
        time.sleep(0.15)

    items = list(seen.values())
    existing = load_existing_items()
    for item in items:
        if item["url"] in existing:
            item.update(existing[item["url"]])
    for item in items:
        item.setdefault("description", "")
        item.setdefault("job_levels", [])
        item.setdefault("languages", [])
        item.setdefault("assessment_length_minutes", None)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote list snapshot with {len(items)} items before detail enrichment", flush=True)

    missing = [item for item in items if not item.get("description")]
    print(f"Detail enrichment remaining: {len(missing)}", flush=True)
    completed = 0
    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as executor:
        futures = {executor.submit(enrich_item, item): item for item in missing}
        for future in as_completed(futures):
            item = futures[future]
            completed += 1
            try:
                item.update(future.result())
                print(f"detail {completed}/{len(missing)}: {item['name']}", flush=True)
            except Exception as exc:
                print(f"detail failed {item['url']}: {exc}", flush=True)
            if completed % 25 == 0:
                OUT.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    return items


def enrich_item(item: dict) -> dict:
    detail = parse_detail(fetch(item["url"], timeout=20))
    patch = {
        "description": detail["description"],
        "job_levels": detail["job_levels"],
        "languages": detail["languages"],
        "assessment_length_minutes": detail["assessment_length_minutes"],
    }
    if detail["detail_test_type"]:
        patch["test_type"] = detail["detail_test_type"]
    time.sleep(0.05)
    return patch


def load_existing_items() -> dict[str, dict]:
    if not OUT.exists():
        return {}
    try:
        raw = json.loads(OUT.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return {item["url"]: item for item in raw if item.get("url")}


def main() -> None:
    OUT.parent.mkdir(exist_ok=True)
    items = scrape()
    OUT.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(items)} catalog items to {OUT}")


if __name__ == "__main__":
    main()
