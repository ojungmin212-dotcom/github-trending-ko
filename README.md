# GitHub 트렌딩 30

[github.com/trending](https://github.com/trending)의 오늘 / 이번 주 / 이번 달 Top 30을 한국어 번역과 함께 보여주는 대시보드입니다.
**GitHub Actions**가 매일 한 번 데이터를 수집해 저장소에 커밋하고, **GitHub Pages**가 정적 페이지로 호스팅합니다.
서버, 유료 서비스, 외부 파이썬 패키지 없이 동작합니다.

- 공개 URL: `https://<사용자명>.github.io/<저장소이름>/`
- 갱신 시각: 매일 09:00 KST (cron `0 0 * * *`, UTC 기준)

## 동작 원리

```
[매일 00:00 UTC] GitHub Actions (.github/workflows/update.yml)
   └─ python scripts/fetch_trending.py
        ├─ github.com/trending?since=daily|weekly|monthly 수집 (재시도 3회)
        ├─ HTML 파싱 → 기간별 목록
        ├─ 30개까지 다른 기간 목록에서 중복 없이 보충 (filled_from에 출처 기록)
        ├─ 설명 한국어 번역 (data/translations.json 캐시 사용, 새 문장만 요청)
        └─ data/trending.json 저장
   └─ 데이터가 바뀌었으면 github-actions[bot]으로 커밋·푸시
        └─ GitHub Pages가 자동 재배포 (보통 1~2분)

[접속할 때] index.html → fetch('data/trending.json?t=타임스탬프') → 화면 표시
```

| 파일 | 역할 |
|---|---|
| `scripts/fetch_trending.py` | 수집·파싱·보충·번역 후 `data/trending.json` 저장 (표준 라이브러리만 사용) |
| `data/trending.json` | 대시보드 데이터. Actions가 매일 갱신 |
| `data/translations.json` | 번역 캐시 (원문 → 번역). 번역에 성공한 문장은 다시 요청하지 않음 |
| `scripts/guides.py` | 각 저장소 README에서 설치 명령·사용법을 규칙으로 추출 (LLM 없음) |
| `data/guides.json` | 저장소별 가이드 캐시 (7일마다 갱신, 30일간 순위에 없으면 삭제) |
| `index.html` | 정적 대시보드. 상대 경로로 JSON을 읽음 (`/저장소이름/` 하위 경로에서도 동작) |
| `.github/workflows/update.yml` | 매일 실행 + 수동 실행(workflow_dispatch) |

### 보충 규칙
GitHub 트렌딩은 기간당 최대 25개(날에 따라 더 적음)만 보여주므로, 30위까지 다른 기간 목록에서 채웁니다.

| 기간 | 보충 순서 |
|---|---|
| 오늘 (daily) | weekly → monthly |
| 이번 주 (weekly) | monthly → daily |
| 이번 달 (monthly) | weekly → daily |

보충된 항목은 화면에 "○○ 순위에서 보충" 배지가 붙고, ▲ 스타 증가량도 출처 기간 기준으로 표시됩니다.

### 안전장치
다음 중 하나라도 해당하면 스크립트가 **기존 `data/trending.json`을 덮어쓰지 않고** 종료 코드 1로 끝납니다.
워크플로가 실패로 표시되고 커밋도 생기지 않으므로, 사이트에는 전날 데이터가 그대로 남습니다.

- 어느 기간이든 파싱 결과가 0개 (GitHub 페이지 구조 변경이나 차단이 의심됨)
- 보충한 뒤에도 어느 기간이 10개 미만

> 기간당 원래 목록이 10개보다 적은 날이 실제로 있습니다 (예: 2026-09-23 daily 8개).
> 그래서 "10개 미만" 판정은 보충한 뒤의 개수로 합니다.

번역에 실패한 문장은 빈 값으로 두고 계속 진행합니다. 실패한 문장은 캐시하지 않으므로 다음 실행 때 다시 시도합니다.

## 디자인

[build.nvidia.com/models](https://build.nvidia.com/models)의 레이아웃과 색을 따랐습니다 (다크 전용).

- 색: 배경 `#0c0c0c`, 카드 `#161616` + `rgba(255,255,255,.2)` 테두리 + 16px 라운드, 포인트 `#76b900`, 보조 텍스트 `#a7a7a7`
- 구조: 48px 상단 내비 → 아이콘+제목 히어로 → 밑줄형 기간 탭 → 왼쪽 필터 사이드바(토글·언어 체크박스) + 오른쪽 검색/정렬 툴바 + 2열 카드 그리드
- 배경 애니메이션: `<canvas id="net">`에 흰색·초록 점(약 1개/10,000px², 반지름 1~1.7px)이 8~45px/s로 떠다니며 100px 안의 점끼리 초록 선으로 연결됩니다. 전체 화면 고정, 투명도 60%. 탭이 안 보이면 멈추고, `prefers-reduced-motion`이면 정지 화면만 그립니다.
- 필터·검색·정렬은 장식이 아니라 실제로 동작합니다 (언어, 번역 유무, 보충 제외, 설치 명령 유무, 텍스트 검색, 순위/스타/증가량/포크 정렬, `Ctrl+K`로 검색창 포커스).
- 900px 이하에서는 사이드바가 "☰ Filters" 버튼으로 접히고 카드가 1열이 됩니다.

## 설치·활용 가이드 기능

각 카드의 **📖 설치·활용 가이드** 버튼을 누르면 다음이 펼쳐집니다.

| 섹션 | 내용 | 출처 |
|---|---|---|
| 무엇인가요? | 한국어 번역 설명, 원문 설명, 홈페이지, 라이선스, 토픽 | 트렌딩 페이지 + GitHub API |
| 설치 방법 | README 코드 블록에서 찾은 설치 명령(`pip`, `npm`, `docker`, `cargo`, `brew` …) + `git clone && cd && …` 한 줄 명령 | README (규칙 추출) |
| 활용 방법 | Usage / Quick Start / Getting Started 섹션 요약과 첫 코드 블록 | README (규칙 추출) |
| AI 에이전트로 바로 쓰기 | Claude Code·Codex 데스크톱 앱에 붙여넣는 프롬프트, `claude "…"` / `codex "…"` CLI 한 줄 명령 | 템플릿 |

모든 항목에 **복사** 버튼이 있습니다.

- 가이드는 LLM 없이 README를 규칙으로 파싱해 만듭니다. 그래서 설치 명령이 빠지거나(README에 코드 블록이 없는 경우) 관련 없는 명령이 섞일 수 있습니다. 화면에도 "README를 우선하세요" 안내를 붙여 두었습니다.
- README는 `raw.githubusercontent.com`에서 받으므로 토큰이나 속도 제한이 없습니다. 라이선스·토픽·홈페이지만 GitHub API를 쓰며, Actions에서는 자동 제공되는 `GITHUB_TOKEN`을, 로컬에서는 `gh auth token`을 사용합니다 (없으면 그 항목만 비워 둡니다).
- 가이드 생성에 실패해도 순위 데이터는 이미 저장된 뒤라 워크플로는 성공으로 끝납니다 (로그에 `[경고]`만 남음).
- 에이전트 프롬프트는 "clone → README대로 설치 → Quick Start 실행 → 사용법·활용 시나리오 3가지를 한국어로 정리" 순서로 시키는 템플릿입니다. CLI 한 줄 명령은 bash와 PowerShell 양쪽에서 그대로 실행되도록 큰따옴표·`$`·백틱을 피했습니다.

## 수동 실행

**웹에서:** 저장소 → **Actions** 탭 → **Update trending data** → **Run workflow** → **Run workflow**

**GitHub CLI로:**
```bash
gh workflow run update.yml
gh run watch                 # 진행 상황 보기
gh run list --workflow=update.yml --limit 5
```

**로컬에서 (테스트용):**
```bash
python scripts/fetch_trending.py
python -m http.server 8000   # 그다음 http://localhost:8000 접속
```
> `index.html`을 더블클릭해 `file://`로 열면 브라우저 보안 정책 때문에 JSON을 읽지 못합니다. 반드시 로컬 서버를 사용하세요.

## 예약 실행에 관해 알아둘 점

- **지연:** GitHub 예약 워크플로는 정시에 실행된다는 보장이 없습니다. 특히 매시 정각처럼 사용자가 몰리는 시간에는 몇 분에서 수십 분 늦게 실행되는 일이 흔합니다. 드물게 한 번 건너뛰기도 합니다.
- **60일 비활성화:** 공개 저장소에서 **60일 동안 저장소 활동(커밋 등)이 없으면** 예약 워크플로가 자동으로 비활성화됩니다.
  이 프로젝트는 워크플로가 매일 데이터를 커밋하므로(보통 `fetched_at`과 순위가 매일 바뀜) 활동이 계속 생겨 대개 비활성화되지 않습니다.
  다만 수집이 계속 실패해 커밋이 멈추면 60일 뒤 비활성화될 수 있습니다.
- **확인 방법:**
  - Actions 탭 → 왼쪽 **Update trending data**. 비활성화되었으면 상단에 "This scheduled workflow is disabled…" 배너와 **Enable workflow** 버튼이 보입니다.
  - CLI: `gh workflow list --all`을 실행해 상태가 `active`인지 확인합니다 (`disabled_inactivity`이면 비활성화된 것).
  - 다시 켜기: `gh workflow enable update.yml` 또는 웹에서 **Enable workflow**를 누릅니다.

## 문제 해결

| 증상 | 확인할 것 / 해결 |
|---|---|
| "마지막 갱신"이 하루 넘게 그대로임 | Actions 탭에서 최근 실행이 실패했는지 확인. 실패했다면 로그의 `[중단]` 메시지 확인 |
| 워크플로가 `[중단] … 하나도 파싱하지 못했습니다`로 실패 | GitHub 트렌딩 HTML 구조가 바뀌었을 가능성이 큼. `parse_trending()`의 정규식(`article.Box-row`, `h2 a`, `p.col-9` 등)을 새 구조에 맞게 수정 |
| 워크플로가 `git push` 단계에서 403 | Settings → Actions → General → **Workflow permissions**를 "Read and write permissions"로 변경 |
| 워크플로가 아예 실행되지 않음 | 위 "60일 비활성화" 항목 확인. 포크한 저장소라면 Actions 탭에서 워크플로를 한 번 활성화해야 함 |
| 한국어 번역 박스가 안 보임 | 번역 엔드포인트가 일시적으로 실패한 것. 다음 실행 때 자동으로 재시도됨 |
| 페이지에 "404" 오류 | Settings → Pages에서 Source가 `main` 브랜치 `/ (root)`인지 확인. 첫 배포는 몇 분 걸릴 수 있음 |
| 데이터는 커밋됐는데 화면이 예전 데이터 | Pages 재배포에 1~2분 걸림. Actions 탭의 `pages-build-deployment` 실행이 끝났는지 확인 |

## 주의

- github.com/trending 페이지와 Google 번역 엔드포인트(`clients5.google.com/translate_a/t`)는 공식 API가 아니므로 예고 없이 바뀌거나 막힐 수 있습니다.
- 한국어 설명은 기계 번역입니다.
