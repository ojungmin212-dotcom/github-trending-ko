# -*- coding: utf-8 -*-
"""수집·보충·안전장치·순위 기록 테스트 (네트워크 없이 실행).

실행: python -m unittest discover -s tests -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import fetch_trending as f  # noqa: E402
import history  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "trending_daily_sample.html"


def article(name, stars=100, gain=10, desc="A tool"):
    """GitHub 트렌딩 article 구조를 흉내 낸 최소 HTML."""
    p = f'<p class="col-9 color-fg-muted my-1 pr-4">{desc}</p>' if desc else ""
    return (f'<article class="Box-row"><h2 class="h3 lh-condensed"><a href="/{name}">{name}</a></h2>{p}'
            f'<span itemprop="programmingLanguage">Python</span>'
            f'<a href="/{name}/stargazers">{stars:,}</a><a href="/{name}/forks">5</a>'
            f'<span class="d-inline-block float-sm-right">{gain} stars today</span></article>')


def page(names):
    return "<html><body>" + "".join(article(n) for n in names) + "</body></html>"


def repos(names, filled=None):
    filled = filled or {}
    return [{"rank": i, "full_name": n, "filled_from": filled.get(n)} for i, n in enumerate(names, 1)]


def result_of(daily, weekly=None, monthly=None):
    return {"daily": {"repos": daily}, "weekly": {"repos": weekly or []}, "monthly": {"repos": monthly or []}}


class ParseTest(unittest.TestCase):
    def test_real_fixture(self):
        rs = f.parse_trending(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(len(rs), 4)
        first = dict(rs[0])
        self.assertTrue(first.pop("description").startswith("Persistent Context Across Sessions"))
        self.assertEqual(first, {
            "full_name": "thedotmack/claude-mem", "url": "https://github.com/thedotmack/claude-mem",
            "language": "TypeScript", "language_color": "#3178c6",
            "stars": 112406, "forks": 9772, "stars_period": 1165})
        self.assertEqual(rs[3]["full_name"], "spotify/portal-ai-plugins")
        self.assertEqual(rs[3]["description"], "")   # 설명 없는 저장소도 빠지지 않는다

    def test_changed_structure_parses_nothing(self):
        self.assertEqual(f.parse_trending("<html><div class='repo'>x</div></html>"), [])

    def test_parse_number(self):
        for text, want in [("1,234", 1234), ("1.2k", 1200), ("12", 12), ("", 0), ("abc", 0)]:
            self.assertEqual(f.parse_number(text), want, text)


class Top30Test(unittest.TestCase):
    def test_fill_without_duplicates(self):
        pages = {
            "daily": [{"full_name": f"d/{i}"} for i in range(13)],
            "weekly": [{"full_name": "d/0"}] + [{"full_name": f"w/{i}"} for i in range(10)],
            "monthly": [{"full_name": f"m/{i}"} for i in range(20)],
        }
        top = f.build_top30("daily", pages)
        names = [r["full_name"] for r in top]
        self.assertEqual(len(top), 30)
        self.assertEqual(len(set(names)), 30)
        self.assertEqual([r["rank"] for r in top], list(range(1, 31)))
        self.assertTrue(all(r["filled_from"] is None for r in top[:13]))
        self.assertEqual(top[13]["full_name"], "w/0")          # weekly 먼저, 중복(d/0) 건너뜀
        self.assertEqual(top[13]["filled_from"], "weekly")
        self.assertEqual(top[23]["filled_from"], "monthly")


class MainTest(unittest.TestCase):
    """main()을 네트워크 없이 돌려 안전장치와 저장 결과를 본다."""

    def run_main(self, pages, history_data=None):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "data").mkdir()
        if history_data is not None:
            (tmp / "data" / "history.json").write_text(json.dumps(history_data), encoding="utf-8")
        patches = [
            mock.patch.object(f, "ROOT", tmp),
            mock.patch.object(f, "DATA_FILE", tmp / "data" / "trending.json"),
            mock.patch.object(f, "CACHE_FILE", tmp / "data" / "translations.json"),
            mock.patch.object(f, "GUIDES_FILE", tmp / "data" / "guides.json"),
            mock.patch.object(f, "HISTORY_FILE", tmp / "data" / "history.json"),
            mock.patch.object(f, "fetch_trending_page", side_effect=lambda s: pages[s]),
            mock.patch.object(f, "translate_ko", side_effect=lambda t: "번역 " + t),
            mock.patch.object(f.guides, "update_guides", side_effect=lambda names, cache, log: {}),
            mock.patch.object(f, "log"),
        ]
        for p in patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in patches])
        return f.main(), tmp / "data"

    def test_stops_when_a_period_is_empty(self):
        code, data = self.run_main({"daily": "", "weekly": page(["a/1"]), "monthly": page(["a/2"])})
        self.assertEqual(code, 1)
        self.assertFalse((data / "trending.json").exists())   # 기존 데이터를 덮어쓰지 않는다

    def test_stops_when_under_ten_after_fill(self):
        code, data = self.run_main({p: page(["a/1", "a/2"]) for p in f.PERIODS})
        self.assertEqual(code, 1)
        self.assertFalse((data / "trending.json").exists())

    def test_saves_with_fill_translation_and_history(self):
        pages = {
            "daily": page([f"d/{i}" for i in range(8)]),       # 원래 8개 — 보충 후 기준이라 통과해야 함
            "weekly": page([f"w/{i}" for i in range(12)]),
            "monthly": page([f"m/{i}" for i in range(15)]),
        }
        code, data = self.run_main(pages)
        self.assertEqual(code, 0)
        out = json.loads((data / "trending.json").read_text(encoding="utf-8"))
        self.assertEqual(out["daily"]["count"], 30)
        self.assertEqual(sum(1 for r in out["daily"]["repos"] if not r["filled_from"]), 8)
        self.assertEqual(out["daily"]["repos"][0]["description_ko"], "번역 A tool")
        self.assertEqual(out["date"], out["fetched_at"][:10])
        self.assertTrue(all(r["first_seen"] == out["date"] for r in out["daily"]["repos"]))
        hist = json.loads((data / "history.json").read_text(encoding="utf-8"))
        self.assertEqual(len(hist["repos"]), 35)

    def test_history_failure_does_not_block_publish(self):
        with mock.patch.object(f.history, "apply", side_effect=RuntimeError("boom")):
            code, data = self.run_main({p: page([f"{p}/{i}" for i in range(12)]) for p in f.PERIODS})
        self.assertEqual(code, 0)
        out = json.loads((data / "trending.json").read_text(encoding="utf-8"))
        self.assertNotIn("date", out)
        self.assertFalse((data / "history.json").exists())


class HistoryTest(unittest.TestCase):
    def test_first_day_everything_is_new(self):
        res = result_of(repos(["a/1", "a/2"]))
        h = history.apply(res, {}, "2026-11-01")
        self.assertEqual(res["daily"]["repos"][0]["first_seen"], "2026-11-01")
        self.assertIsNone(res["daily"]["repos"][0]["prev_rank"])
        self.assertEqual(res["daily"]["repos"][0]["streak"], 1)
        self.assertEqual(h["repos"]["a/1"], {"first_seen": "2026-11-01", "last_seen": "2026-11-01"})

    def test_next_day_rank_change_streak_and_new(self):
        h = history.apply(result_of(repos(["a/1", "a/2"])), {}, "2026-11-01")
        res = result_of(repos(["a/2", "b/9", "a/1"]))
        history.apply(res, h, "2026-11-02")
        a2, b9, a1 = res["daily"]["repos"]
        self.assertEqual((a2["prev_rank"], a2["streak"], a2["first_seen"]), (2, 2, "2026-11-01"))
        self.assertEqual((b9["prev_rank"], b9["streak"], b9["first_seen"]), (None, 1, "2026-11-02"))
        self.assertEqual((a1["prev_rank"], a1["streak"]), (1, 2))

    def test_reentry_is_not_new(self):
        h = history.apply(result_of(repos(["a/1"])), {}, "2026-11-01")
        h = history.apply(result_of(repos(["a/2"])), h, "2026-11-02")
        res = result_of(repos(["a/1"]))
        history.apply(res, h, "2026-11-03")
        r = res["daily"]["repos"][0]
        self.assertEqual((r["first_seen"], r["prev_rank"], r["streak"]), ("2026-11-01", None, 1))

    def test_same_day_rerun_gives_same_result(self):
        h1 = history.apply(result_of(repos(["a/1", "a/2"])), {}, "2026-11-01")
        first = result_of(repos(["a/2", "a/1"]))
        h2 = history.apply(first, h1, "2026-11-02")
        again = result_of(repos(["a/2", "a/1"]))
        h3 = history.apply(again, h2, "2026-11-02")
        self.assertEqual(first, again)
        self.assertEqual(h2, h3)

    def test_filled_items_get_first_seen_only(self):
        res = result_of(repos(["a/1", "w/1"], filled={"w/1": "weekly"}), repos(["w/1"]))
        history.apply(res, {}, "2026-11-01")
        filled = res["daily"]["repos"][1]
        self.assertEqual(filled["first_seen"], "2026-11-01")
        self.assertNotIn("prev_rank", filled)
        self.assertNotIn("streak", filled)

    def test_prune_old_repos(self):
        h = history.apply(result_of(repos(["old/1"])), {}, "2026-01-01")
        h = history.apply(result_of(repos(["new/1"])), h, "2026-08-01")
        self.assertNotIn("old/1", h["repos"])
        self.assertIn("new/1", h["repos"])


class TranslateTest(unittest.TestCase):
    def test_same_text_is_not_repeated(self):
        with mock.patch.object(f, "http_get", return_value='[["안녕", "ko"]]'):
            self.assertEqual(f.translate_ko("안녕"), "")
        with mock.patch.object(f, "http_get", return_value='[["도구", "en"]]'):
            self.assertEqual(f.translate_ko("tool"), "도구")

    def test_failure_returns_none(self):
        with mock.patch.object(f, "http_get", side_effect=OSError("down")), mock.patch.object(f, "log"):
            self.assertIsNone(f.translate_ko("tool"))


if __name__ == "__main__":
    unittest.main()
