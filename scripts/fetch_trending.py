# -*- coding: utf-8 -*-
"""GitHub 트렌딩 Top 30 수집 스크립트 (GitHub Actions에서 매일 실행).

github.com/trending 의 daily / weekly / monthly 세 페이지를 수집·파싱하고,
설명을 한국어로 번역해 data/trending.json 으로 저장한다.

- GitHub 트렌딩은 기간당 최대 25개이므로 26~30위는 다른 기간 목록에서
  중복 없이 보충한다 (보충 항목은 filled_from 에 출처 기간 기록).
- 번역 결과는 data/translations.json 에 캐시해 같은 문장을 재요청하지 않는다.
- 어느 기간이든 파싱 결과가 0개이거나 보충 후 10개 미만이면
  기존 데이터를 덮어쓰지 않고 에러 코드로 종료한다.

Python 표준 라이브러리만 사용한다.
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "trending.json"
CACHE_FILE = ROOT / "data" / "translations.json"

PERIODS = ["daily", "weekly", "monthly"]
TOP_N = 30
MIN_REPOS = 10  # 이보다 적으면 파싱 실패로 보고 게시하지 않음
RETRIES = 3
KST = timezone(timedelta(hours=9))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

FALLBACK_ORDER = {
    "daily": ["weekly", "monthly"],
    "weekly": ["monthly", "daily"],
    "monthly": ["weekly", "daily"],
}


def log(msg):
    print(msg, flush=True)


def http_get(url, timeout):
    """GET 요청. 실패하면 최대 RETRIES회까지 재시도."""
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            last_err = e
            if attempt < RETRIES:
                time.sleep(2 * attempt)
    raise last_err


def fetch_trending_page(since):
    return http_get(f"https://github.com/trending?since={since}", timeout=20)


def strip_tags(html):
    return unescape(re.sub(r"<[^>]+>", "", html)).strip()


def parse_number(text):
    """'1,234' 또는 '1.2k' 형태를 정수로 변환."""
    text = text.strip().lower().replace(",", "")
    if not text:
        return 0
    try:
        if text.endswith("k"):
            return int(float(text[:-1]) * 1000)
        return int(float(text))
    except ValueError:
        return 0


def parse_trending(html):
    repos = []
    # 각 저장소는 <article class="Box-row"> 블록
    articles = re.split(r'<article[^>]*class="Box-row"[^>]*>', html)[1:]
    for block in articles:
        block = block.split("</article>")[0]

        m = re.search(r'<h2[^>]*>.*?<a[^>]*href="/([^/"]+/[^/"]+)"', block, re.S)
        if not m:
            continue
        full_name = m.group(1)

        desc = ""
        md = re.search(r'<p[^>]*class="[^"]*col-9[^"]*"[^>]*>(.*?)</p>', block, re.S)
        if md:
            desc = strip_tags(md.group(1))

        lang = ""
        ml = re.search(r'<span[^>]*itemprop="programmingLanguage"[^>]*>(.*?)</span>', block, re.S)
        if ml:
            lang = strip_tags(ml.group(1))

        lang_color = ""
        mc = re.search(r'style="background-color:\s*([^";]+)', block)
        if mc:
            lang_color = mc.group(1).strip()

        stars = 0
        ms = re.search(r'href="/%s/stargazers"[^>]*>(.*?)</a>' % re.escape(full_name), block, re.S)
        if ms:
            stars = parse_number(strip_tags(ms.group(1)))

        forks = 0
        mf = re.search(r'href="/%s/forks"[^>]*>(.*?)</a>' % re.escape(full_name), block, re.S)
        if mf:
            forks = parse_number(strip_tags(mf.group(1)))

        stars_period = 0
        mp = re.search(
            r'<span[^>]*class="[^"]*float-sm-right[^"]*"[^>]*>(.*?)</span>', block, re.S)
        if mp:
            num = re.search(r'[\d,.]+k?', strip_tags(mp.group(1)), re.I)
            if num:
                stars_period = parse_number(num.group(0))

        repos.append({
            "full_name": full_name,
            "url": f"https://github.com/{full_name}",
            "description": desc,
            "language": lang,
            "language_color": lang_color,
            "stars": stars,
            "forks": forks,
            "stars_period": stars_period,
        })
    return repos


def build_top30(since, pages):
    """선택한 기간 목록 + 다른 기간 목록에서 중복 없이 채워 30개 구성."""
    result = [dict(r, filled_from=None) for r in pages[since]]
    seen = {r["full_name"] for r in result}
    for fb in FALLBACK_ORDER[since]:
        for r in pages[fb]:
            if len(result) >= TOP_N:
                break
            if r["full_name"] in seen:
                continue
            seen.add(r["full_name"])
            result.append(dict(r, filled_from=fb))
    return [{"rank": i, **r} for i, r in enumerate(result[:TOP_N], 1)]


# ---- 번역 ----

def load_cache():
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def translate_ko(text):
    """Google 번역 무료 엔드포인트로 한국어 번역. 실패하면 None."""
    url = ("https://clients5.google.com/translate_a/t"
           "?client=dict-chrome-ex&sl=auto&tl=ko&q=" + urllib.parse.quote(text))
    try:
        data = json.loads(http_get(url, timeout=10))
        # 응답 형태: [["번역문", "감지된 언어"]] 또는 ["번역문"]
        item = data[0] if data else ""
        result = (item[0] if isinstance(item, list) else item).strip()
    except Exception as e:
        log(f"  번역 실패: {text[:40]!r} ({e})")
        return None
    # 원문이 이미 한국어라 번역 결과가 같으면 중복 표시하지 않음
    return "" if result == text.strip() else result


def add_translations(all_repos, cache):
    texts = {r["description"] for r in all_repos if r["description"]}
    todo = sorted(t for t in texts if t not in cache)
    log(f"번역: 전체 {len(texts)}문장 중 캐시 적중 {len(texts) - len(todo)}, 신규 요청 {len(todo)}")
    with ThreadPoolExecutor(max_workers=4) as pool:
        for text, ko in zip(todo, pool.map(translate_ko, todo)):
            if ko is not None:  # 실패한 결과는 캐시하지 않아 다음 실행 때 재시도
                cache[text] = ko
    for r in all_repos:
        r["description_ko"] = cache.get(r["description"], "") if r["description"] else ""


def write_json(path, obj):
    tmp = path.with_suffix(".tmp")
    # newline="\n": Windows에서 실행해도 LF로 저장해 Actions(Linux) 커밋과 줄바꿈 차이가 나지 않게
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8", newline="\n")
    tmp.replace(path)


def main():
    pages = {}
    for since in PERIODS:
        try:
            pages[since] = parse_trending(fetch_trending_page(since))
        except Exception as e:
            log(f"[오류] {since} 페이지 수집 실패: {e}")
            pages[since] = []
        log(f"{since}: {len(pages[since])}개 파싱")

    # 안전장치 1: 한 기간이라도 0개면 페이지 구조 변경·차단으로 판단
    empty = [p for p in PERIODS if not pages[p]]
    if empty:
        log(f"[중단] {', '.join(empty)} 기간을 하나도 파싱하지 못했습니다. "
            "GitHub 페이지 구조 변경 또는 차단 가능성이 있어 기존 데이터를 유지합니다.")
        return 1

    result = {"fetched_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")}
    for since in PERIODS:
        repos = build_top30(since, pages)
        result[since] = {"since": since, "count": len(repos), "repos": repos}

    # 안전장치 2: 보충 후에도 MIN_REPOS개 미만이면 게시하지 않음
    # (GitHub 트렌딩은 날에 따라 기간당 25개보다 적게 노출하기도 해서 보충 후 개수로 판단)
    bad = [p for p in PERIODS if result[p]["count"] < MIN_REPOS]
    if bad:
        log(f"[중단] {', '.join(bad)} 기간이 보충 후에도 {MIN_REPOS}개 미만입니다. "
            "기존 데이터를 유지합니다.")
        return 1

    cache = load_cache()
    add_translations([r for p in PERIODS for r in result[p]["repos"]], cache)

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    write_json(CACHE_FILE, dict(sorted(cache.items())))
    write_json(DATA_FILE, result)
    log(f"저장 완료: {DATA_FILE.relative_to(ROOT).as_posix()} - "
        + ", ".join(f"{p} {result[p]['count']}개" for p in PERIODS)
        + f" ({result['fetched_at']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
