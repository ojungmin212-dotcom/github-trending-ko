# -*- coding: utf-8 -*-
"""순위 기록(data/history.json) — 처음 등장·순위 변화·연속 일수 계산.

GitHub 트렌딩은 날마다 겹치는 저장소가 많아 "무엇이 새로 올라왔나"를 보여 주려면
이전 실행의 순위를 기억해야 한다. Actions는 얕은 clone(depth 1)이라 git 기록을
읽을 수 없으므로 상태를 파일로 들고 다닌다.

비교 기준은 GitHub이 실제로 준 원래 순위(filled_from 이 없는 항목)뿐이다.
보충 항목의 자리 번호는 날마다 의미 없이 바뀌므로 순위 변화·연속 일수를 붙이지 않는다.

data/history.json 형식:
{
  "repos": {"owner/name": {"first_seen": "YYYY-MM-DD", "last_seen": "YYYY-MM-DD"}},
  "periods": {
    "daily": {"date": "YYYY-MM-DD", "ranks": {name: rank}, "streak": {name: n},
              "prev": {"date": ..., "ranks": {...}, "streak": {...}}},
    ...
  }
}
같은 날 다시 실행하면 저장된 "prev"를 다시 기준으로 쓰므로 결과가 바뀌지 않는다.
연속 일수는 "연속 실행 횟수"다. 실행은 매일 한 번이라 일수와 같다.

처음 한 번은 git 기록에서 다시 만든다:
    python scripts/history.py --rebuild
(data/history.json 을 새로 쓰고, 현재 data/trending.json 에도 결과를 붙인다)

Python 표준 라이브러리만 사용한다.
"""

import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

PERIODS = ("daily", "weekly", "monthly")
PRUNE_DAYS = 180  # 이 기간 동안 한 번도 안 보인 저장소는 기록에서 지운다


def load(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def apply(result, history, today):
    """result 의 각 저장소에 first_seen / prev_rank / streak 를 붙이고 새 기록을 돌려준다.

    result: {"daily": {"repos": [...]}, "weekly": ..., "monthly": ...}
    history: load() 결과 (비어 있어도 됨)
    today: "YYYY-MM-DD" (KST 기준 수집 날짜)
    """
    history = history or {}
    seen = {k: dict(v) for k, v in (history.get("repos") or {}).items()}
    old_periods = history.get("periods") or {}

    # 1) 처음 등장 날짜: 세 기간의 원래 순위에 한 번이라도 오르면 "본 것"으로 친다
    for p in PERIODS:
        for r in result[p]["repos"]:
            if r.get("filled_from"):
                continue
            name = r["full_name"]
            entry = seen.setdefault(name, {"first_seen": today})
            entry["last_seen"] = today

    # 2) 기간별 순위 변화·연속 일수
    periods = {}
    for p in PERIODS:
        stored = old_periods.get(p) or {}
        if stored.get("date") == today:   # 같은 날 재실행: 그날의 기준을 그대로 쓴다
            base = stored.get("prev") or {}
        else:
            base = stored
        base_ranks = base.get("ranks") or {}
        base_streak = base.get("streak") or {}

        ranks, streak = {}, {}
        for r in result[p]["repos"]:
            name = r["full_name"]
            r["first_seen"] = seen.get(name, {}).get("first_seen", today)
            if r.get("filled_from"):
                continue
            ranks[name] = r["rank"]
            streak[name] = base_streak.get(name, 0) + 1 if name in base_ranks else 1
            r["prev_rank"] = base_ranks.get(name)
            r["streak"] = streak[name]
        periods[p] = {
            "date": today,
            "ranks": ranks,
            "streak": streak,
            "prev": {"date": base.get("date"), "ranks": base_ranks, "streak": base_streak},
        }

    # 3) 오래 안 보인 저장소 정리 (기록이 끝없이 커지지 않게)
    cutoff = (date.fromisoformat(today) - timedelta(days=PRUNE_DAYS)).isoformat()
    seen = {k: v for k, v in seen.items() if v.get("last_seen", today) >= cutoff}

    return {"repos": dict(sorted(seen.items())), "periods": periods}


def rebuild_from_git(root):
    """data/trending.json 의 git 기록을 오래된 것부터 다시 재생해 기록을 만든다."""
    shas = subprocess.check_output(
        ["git", "log", "--reverse", "--format=%H", "--", "data/trending.json"],
        cwd=root, text=True).split()
    history = {}
    used = 0
    for sha in shas:
        try:
            snap = json.loads(subprocess.check_output(
                ["git", "show", f"{sha}:data/trending.json"], cwd=root, encoding="utf-8"))
            today = snap["fetched_at"][:10]
            if not all(isinstance(snap.get(p, {}).get("repos"), list) for p in PERIODS):
                continue
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, TypeError):
            continue
        history = apply(snap, history, today)
        used += 1
    return history, used


def main(argv):
    if "--rebuild" not in argv:
        print("사용법: python scripts/history.py --rebuild")
        return 2
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from fetch_trending import ROOT, DATA_FILE, HISTORY_FILE, write_json  # noqa: E402

    history, used = rebuild_from_git(ROOT)
    # 현재 파일(커밋되지 않은 변경 포함)에도 같은 계산을 붙여 바로 화면에 보이게 한다
    current = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    today = current["fetched_at"][:10]
    history = apply(current, history, today)
    current["date"] = today
    write_json(DATA_FILE, current)
    write_json(HISTORY_FILE, history)
    new_today = {r["full_name"] for p in PERIODS for r in current[p]["repos"]
                 if r.get("first_seen") == today}
    print(f"기록 재생성: 스냅샷 {used}개 사용, 저장소 {len(history['repos'])}개, "
          f"{today} 처음 등장 {len(new_today)}개")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
