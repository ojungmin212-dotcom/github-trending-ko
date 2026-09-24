# -*- coding: utf-8 -*-
"""저장소 README에서 설치·활용 정보를 추출해 data/guides.json 에 저장한다.

LLM 없이 규칙 기반으로 동작한다 (표준 라이브러리만 사용).
- README는 raw.githubusercontent.com 에서 받는다 (토큰·속도 제한 없음).
- 저장소 메타데이터(라이선스·홈페이지·토픽)는 GITHUB_TOKEN 이 있을 때만 API 로 받는다.
- 결과는 README 가 바뀌어도 7일마다만 다시 받는다 (guides.json 캐시).

추출 항목 (full_name 별):
  install      : README 코드 블록에서 찾은 설치 명령 (최대 6개)
  usage_text   : Usage / Quick Start 류 섹션의 본문 요약 (plain text)
  usage_code   : 그 섹션의 첫 코드 블록
  license, homepage, topics, default_branch, readme_url, fetched
"""

import json
import os
import re
import subprocess
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html import unescape

README_CANDIDATES = ["README.md", "readme.md", "Readme.md", "README.MD", "README.rst", "README"]
REFRESH_DAYS = 7
MAX_INSTALL = 6
MAX_USAGE_CHARS = 700
MAX_CODE_LINES = 18

INSTALL_TOOLS = (
    r"pip3?|pipx|uv|uvx|python3? -m pip|npm|npx|pnpm|yarn|bun|deno|cargo|go|brew|docker(?: compose)?|"
    r"apt(?:-get)?|dnf|pacman|conda|mamba|gem|bundle|dotnet|composer|mvn|gradle|curl|wget|sh|bash|"
    r"winget|choco|scoop|helm|kubectl|flatpak|snap|nix|git clone|make|cmake|swift|xcodebuild|ollama|"
    r"claude|codex|gh"
)
INSTALL_LINE = re.compile(r"^\s*(?:[$>]\s*)?(?:sudo\s+)?((?:%s)(?=\s)[^\n]*)$" % INSTALL_TOOLS, re.M)
TREE_LINE = re.compile(r"^\S+/\s|[├└│]")  # 디렉터리 트리 표기
INSTALL_HINT = re.compile(r"\b(install|clone|add|pull|run|get|create|init|setup|-g|--global)\b|@latest|\.sh\b", re.I)
INSTALL_HEADING = re.compile(r"install|setup|set up|getting started|get started|quick ?start|quickstart|prerequisit|requirement|download", re.I)
USAGE_HEADING = re.compile(r"usage|how to use|how it works|quick ?start|quickstart|getting started|get started|example|tutorial|run(ning)?\b|basic|demo|features?", re.I)
SKIP_HEADING = re.compile(r"contribut|license|licence|sponsor|star history|citation|acknowledg|changelog|roadmap|faq|community|support us|donat", re.I)


def _headers():
    h = {"User-Agent": "github-trending-ko (https://github.com/ojungmin212-dotcom/github-trending-ko)"}
    return h


def _github_token():
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok
    try:  # 로컬 실행 시 gh CLI 로그인 토큰 재사용 (없으면 메타데이터 생략)
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=10, shell=os.name == "nt")
        return out.stdout.strip() or None
    except Exception:
        return None


def _get(url, timeout=15, headers=None):
    req = urllib.request.Request(url, headers={**_headers(), **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_readme(full_name):
    """raw.githubusercontent.com 에서 README 를 받는다. (본문, url) 또는 (None, None)."""
    for name in README_CANDIDATES:
        url = f"https://raw.githubusercontent.com/{full_name}/HEAD/{name}"
        try:
            return _get(url)[:200_000], f"https://github.com/{full_name}#readme"
        except Exception:
            continue
    return None, None


def fetch_meta(full_name, token):
    if not token:
        return {}
    try:
        data = json.loads(_get(f"https://api.github.com/repos/{full_name}", headers={
            "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}))
    except Exception:
        return {}
    lic = (data.get("license") or {}).get("spdx_id") or ""
    return {
        "license": "" if lic == "NOASSERTION" else lic,
        "homepage": data.get("homepage") or "",
        "topics": (data.get("topics") or [])[:8],
        "default_branch": data.get("default_branch") or "main",
    }


# ---- README 파싱 ----

FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
HEADING = re.compile(r"^(#{1,4})\s+(.+?)\s*#*\s*$", re.M)


def _sections(md):
    """(레벨, 제목, 본문) 목록. 첫 헤딩 앞부분은 레벨 0, 제목 ''."""
    out, pos, level, title = [], 0, 0, ""
    fences = [(f.start(), f.end()) for f in FENCE.finditer(md)]
    for m in HEADING.finditer(md):
        if any(s <= m.start() < e for s, e in fences):  # 코드 블록 안의 '# 주석'은 헤딩이 아님
            continue
        out.append((level, title, md[pos:m.start()]))
        level, title, pos = len(m.group(1)), m.group(2), m.end()
    out.append((level, title, md[pos:]))
    return out


def _plain(md):
    """마크다운 → 짧은 plain text (배지·이미지·HTML·링크 제거)."""
    t = FENCE.sub(" ", md)
    t = re.sub(r"^\s*```.*$", " ", t, flags=re.M)          # 닫히지 않은 펜스 잔여물
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)           # 이미지
    t = re.sub(r"\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)", " ", t)  # 배지 링크
    t = re.sub(r"<[^>]+>", " ", t)                          # HTML
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)          # 링크 → 텍스트
    t = re.sub(r"`([^`\n]+)`", r"\1", t)
    t = re.sub(r"^\s*[-*+]\s+", "• ", t, flags=re.M)
    t = re.sub(r"^\s*\|.*\|\s*$", " ", t, flags=re.M)      # 표
    t = re.sub(r"[*_]{1,3}([^*_\n]+)[*_]{1,3}", r"\1", t)
    t = unescape(t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t.strip()


def _truncate(text, limit):
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for sep in ("\n", ". ", " "):
        i = cut.rfind(sep)
        if i > limit * 0.6:
            cut = cut[:i]
            break
    return cut.rstrip(" .,;:") + "…"


def _install_from_blocks(blocks):
    found = []
    for block in blocks:
        lines = block.splitlines()
        i = 0
        while i < len(lines):
            m = INSTALL_LINE.match(lines[i])
            i += 1
            if not m:
                continue
            line = m.group(1).strip()
            # 줄 끝 '\' 로 이어지는 명령은 다음 줄까지 합친다 (docker run … \ 등)
            while line.endswith("\\") and i < len(lines):
                line = line[:-1].rstrip() + " " + lines[i].strip()
                i += 1
            line = re.sub(r"\s{2,}(#.*)$", r"  \1", line)  # 주석 앞 긴 공백 정리
            if len(line) > 220 or line.startswith(("#", "//")) or TREE_LINE.search(line):
                continue
            if not INSTALL_HINT.search(line) and not line.startswith(("npx", "uvx", "docker", "curl", "wget")):
                continue
            if line not in found:
                found.append(line)
            if len(found) >= MAX_INSTALL:
                return found
    return found


def _first_code(md, max_lines=MAX_CODE_LINES):
    for m in FENCE.finditer(md):
        code = m.group(1).strip("\n")
        if code.strip():
            lines = code.splitlines()
            if len(lines) > max_lines:
                lines = lines[:max_lines] + ["…"]
            return "\n".join(lines)
    return ""


def extract_guide(md):
    """README 마크다운에서 설치 명령·사용법 요약을 추출."""
    secs = _sections(md)
    # 1) 설치 명령: 설치 관련 섹션 우선, 없으면 README 전체 코드 블록
    install_blocks = [FENCE.findall(body) for lvl, title, body in secs if INSTALL_HEADING.search(title)]
    install = _install_from_blocks([b for bs in install_blocks for b in bs])
    if len(install) < 2:
        for line in _install_from_blocks(FENCE.findall(md)):
            if line not in install:
                install.append(line)
            if len(install) >= MAX_INSTALL:
                break

    # 2) 사용법: usage 류 섹션 중 본문이 있는 첫 섹션
    usage_text, usage_code, usage_title = "", "", ""
    for lvl, title, body in secs:
        if not title or SKIP_HEADING.search(title) or not USAGE_HEADING.search(title):
            continue
        text = _plain(body)
        code = _first_code(body)
        if len(text) < 40 and not code:
            continue
        usage_text, usage_code, usage_title = _truncate(text, MAX_USAGE_CHARS), code, title.strip()
        break
    if not usage_text:  # 3) 없으면 README 앞부분 소개 문단 (제목 앞 배지·스폰서 영역은 제외)
        for lvl, title, body in secs:
            text = _plain(body)
            if lvl == 0 or SKIP_HEADING.search(title) or re.search(r"sponsor", text[:200], re.I):
                continue
            if len(text) >= 80:
                usage_text, usage_title = _truncate(text, MAX_USAGE_CHARS), title.strip() or "About"
                break
    return {"install": install, "usage_title": _plain(usage_title)[:60], "usage_text": usage_text, "usage_code": usage_code}


def _fetch_one(args):
    full_name, token = args
    md, url = fetch_readme(full_name)
    entry = {"fetched": time.strftime("%Y-%m-%d"), "readme_url": url or f"https://github.com/{full_name}"}
    if md:
        entry.update(extract_guide(md))
    else:
        entry.update({"install": [], "usage_title": "", "usage_text": "", "usage_code": ""})
    entry.update(fetch_meta(full_name, token))
    return full_name, entry


def update_guides(full_names, cache, log=print):
    """필요한 저장소만 새로 받아 cache(dict)를 갱신하고 정리해서 돌려준다."""
    today = time.time()
    def stale(e):
        try:
            return today - time.mktime(time.strptime(e.get("fetched", ""), "%Y-%m-%d")) > REFRESH_DAYS * 86400
        except ValueError:
            return True
    todo = [n for n in full_names if n not in cache or stale(cache[n])]
    token = _github_token()
    log(f"가이드: 대상 {len(full_names)}개 중 캐시 적중 {len(full_names) - len(todo)}, 신규/갱신 {len(todo)}"
        + ("" if token else " (토큰 없음 → 라이선스·토픽 생략)"))
    with ThreadPoolExecutor(max_workers=4) as pool:
        for name, entry in pool.map(_fetch_one, [(n, token) for n in todo]):
            cache[name] = entry
    # 현재 목록에 없는 항목은 30일 지나면 정리
    keep = set(full_names)
    for name in list(cache):
        if name not in keep:
            try:
                age = today - time.mktime(time.strptime(cache[name].get("fetched", ""), "%Y-%m-%d"))
            except ValueError:
                age = 1e12
            if age > 30 * 86400:
                del cache[name]
    return dict(sorted(cache.items()))
