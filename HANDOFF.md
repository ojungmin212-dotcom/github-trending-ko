# HANDOFF — 오박사의 GitHub Trending Space

> 다른 계정·다른 Claude Code 세션에서 이어서 작업하기 위한 인수인계 문서.
> 작성: 2026-10-09 · 기준 커밋: `e64d2d6` (origin/main과 동기화됨, 미커밋 변경 없음)

## 1. 프로젝트 한눈에 보기

GitHub 트렌딩(오늘/이번 주/이번 달) Top 30을 **한국어 번역 + 설치·활용 가이드 + AI 에이전트 프롬프트**와 함께 보여주는 정적 대시보드.
Claude API·유료 서비스·서버 없이 **GitHub Actions(매일 수집) + GitHub Pages(호스팅)** 만으로 돈다.

| 항목 | 값 |
|---|---|
| 공개 URL | https://ojungmin212-dotcom.github.io/github-trending-ko/ |
| 저장소 | https://github.com/ojungmin212-dotcom/github-trending-ko (public, 브랜치 `main`) |
| Pages | legacy build, source `main` / `(root)` |
| 로컬 경로 | `E:\클로드\29-09-23_1` (이전: `C:\Users\Win\Desktop\클로드\29-09-23_1` — 옛 문서·메모리에 이 경로가 남아 있음) |
| 사용자 | 한국어 사용자. **모든 답변·보고·질문은 한국어로** (명시적 요청) |

### 아키텍처

```
[매일 cron "0 0 * * *" UTC] .github/workflows/update.yml
  └─ python scripts/fetch_trending.py           (표준 라이브러리만)
       ├─ github.com/trending?since=daily|weekly|monthly 수집 (UA 헤더, 재시도 3회)
       ├─ parse_trending(): <article class="Box-row"> 정규식 파싱
       ├─ build_top30(): 다른 기간 목록에서 중복 없이 30개까지 보충 (filled_from)
       ├─ 번역: clients5.google.com/translate_a/t (동시 4, data/translations.json 캐시)
       ├─ 안전장치 통과 시 data/trending.json 저장
       └─ scripts/guides.py: README(raw.githubusercontent.com) 규칙 파싱 → data/guides.json
  └─ 변경 있으면 github-actions[bot] 커밋 → git pull --rebase → push
       └─ pages-build-deployment 자동 실행 (1~2분)

[브라우저] index.html (단일 파일, 빌드 없음)
  ├─ fetch('data/trending.json?t=타임스탬프')  ← 상대 경로 필수 (/github-trending-ko/ 하위 경로)
  ├─ fetch('data/guides.json?t=…')            ← 실패해도 순위 표시는 유지
  ├─ <canvas id="net"> 점·선 배경 애니메이션
  └─ localStorage 'gtk-favs-v1' 관심 레포
```

### 파일

| 파일 | 역할 |
|---|---|
| `scripts/fetch_trending.py` | 수집·파싱·보충·번역·안전장치·저장 (진입점) |
| `scripts/guides.py` | README에서 설치 명령·사용법 규칙 추출 (LLM 없음) |
| `data/trending.json` | `{fetched_at, daily|weekly|monthly: {since, count, repos[]}}` |
| `data/translations.json` | 번역 캐시 `{원문: 번역}` — 성공한 것만 저장 |
| `data/guides.json` | `{full_name: {install[], usage_title, usage_text, usage_code, license, homepage, topics, readme_url, fetched}}` 7일 캐시, 순위 밖 30일 후 삭제 |
| `index.html` | 대시보드 전부 (CSS·JS 인라인, 약 900줄) |
| `.github/workflows/update.yml` | schedule + workflow_dispatch, `contents: write` |
| `.claude/launch.json` | 로컬 미리보기 서버 `python -m http.server 8766` (gitignore 대상) |
| `README.md` | 사용자용 설명 (동작 원리·수동 실행·문제 해결) |

## 2. 완료 / 진행 중 / 다음 단계

### ✅ 완료 (시간순)
1. 수집 스크립트 + 30위 보충 + 번역 캐시 + 안전장치 (`a318362`)
2. Actions 워크플로 + Pages 배포, 실제 실행·커밋·Pages 반영 검증
3. JSON을 항상 LF로 저장 (`b6ee99a`) — Windows CRLF 때문에 첫 봇 커밋이 1236줄 diff였음
4. 설치·활용 가이드 + Claude Code/Codex 프롬프트·CLI 한 줄 명령 + 복사 버튼 (`758f736`)
5. build.nvidia.com/models 디자인 모방 + 점·선 캔버스 애니메이션 + 동작하는 필터·검색·정렬 (`993b3b0`)
6. 제목 "오박사의 GitHub Trending Space" (`c492181`)
7. 관심 레포(찜하기) + `?fav=` 공유 링크로 기기 간 이동 + 모바일 그리드 넘침 수정 (`c044802`)
8. 이후 매일 봇 커밋 정상 (2026-09-23 ~ 10-08, 16회 연속 success)

### 🔄 진행 중
- 없음. 작업 트리는 깨끗하다.

### ⏭ 다음 단계 (우선순위 순)
1. **예약 실행 지연 대응** (아래 4장 버그 #1). cron을 정각이 아닌 분으로 옮기거나(예: `"17 23 * * *"` = 08:17 KST), 실제 갱신 시각에 맞게 푸터·README 문구를 고친다. 어느 쪽인지는 사용자에게 확인.
2. **옛 Claude 루틴 정리 여부 확인.** 이 프로젝트 전에 쓰던 Claude Code 루틴(`trig_01XrndG9HypGCBXDV2h32ooz`, 매시간 :50, 아티팩트 버전 갱신)이 아직 켜져 있을 수 있다. 사용자에게 비활성화 여부를 물었으나 **답을 받지 못함** — 임의로 끄지 말 것. (다른 계정에서는 접근 불가할 수 있음)
3. 로고 옆 "GitHub 트렌딩", 상단 메뉴 "Trending"도 새 제목에 맞출지 사용자에게 확인 (이전에 제안만 함).
4. (선택) 더 나은 가이드: 무료 LLM을 Actions secret으로 붙이고 실패 시 현재 규칙 추출로 폴백. 사용자 원칙(Claude API·유료 금지) 때문에 **사용자 승인 전에는 하지 말 것**.

## 3. 설계 결정과 이유

| 결정 | 이유 |
|---|---|
| 서버 없이 Actions + Pages | 사용자 요구: Claude 없이 매일 자동, 무료, 로그인 없이 공개 URL |
| Python **표준 라이브러리만** | 사용자 요구. `pip install` 금지 |
| 안전장치 = "파싱 0개" 또는 "**보충 후** 10개 미만"이면 중단 | 원 요구는 "원시 10개 미만이면 중단"이었으나 GitHub이 실제로 daily 8개만 주는 날이 있어 매일 실패하게 됨. **원시 개수 기준으로 되돌리지 말 것** |
| 번역 실패는 캐시하지 않음 | 다음 실행 때 자동 재시도 |
| JSON `newline="\n"` | Windows 로컬 실행과 Linux Actions의 줄바꿈 차이로 전체 diff가 생기던 문제 |
| 워크플로에서 push 전 `git pull --rebase` | 실행 중 다른 push와의 경합 방지 |
| 가이드는 README 규칙 파싱 (LLM 없음) | Claude API·유료 서비스 금지 원칙. raw.githubusercontent.com은 토큰·속도 제한 없음 |
| 가이드 실패는 `[경고]`만, 워크플로 성공 | 순위 데이터가 가이드 때문에 막히면 안 됨 |
| CLI 한 줄 명령에서 `"`·`$`·백틱 회피 | bash·PowerShell 양쪽에서 그대로 실행되게 |
| 디자인 다크 전용 | 모방 대상(build.nvidia.com)에 라이트 테마가 없음. 사용자가 요청한 디자인이므로 **이전 라이트/다크 카드 디자인으로 되돌리지 말 것** |
| 폰트 Inter + Noto Sans KR | NVIDIA Sans는 사내 폰트라 사용 불가 |
| 관심 레포 = localStorage `gtk-favs-v1` | 서버가 없음. 기기 간 이동은 `?fav=a/b,c/d` 링크 **합치기**(기존 유지). **키·형식 변경 시 마이그레이션 필수** |
| 데이터 fetch는 상대 경로 + `?t=` | Pages 프로젝트 사이트 하위 경로 + CDN 캐시 회피 |

## 4. 알려진 버그 · 막혔던 지점 · 실패한 접근

### 알려진 문제
1. **예약 실행이 4~5시간 늦음.** cron은 00:00 UTC(09:00 KST)인데 실제 실행은 **매일 12:55~14:36 KST**(16일 관측). 정각 cron은 GitHub 부하가 몰려 지연되는 것으로 보임. 푸터·README의 "09:00 KST" 문구가 사실과 다름.
2. **GitHub 트렌딩이 25개보다 적게 노출됨.** 관측: daily 8~14, weekly 20~21, monthly 22. 보충으로 30개는 채워짐.
3. **가이드 추출은 휴리스틱.** 50개 중 설치 명령 44개, 사용법 49개 추출. 엉뚱한 명령이 섞일 수 있음(화면에 "README 우선" 안내 있음).
4. **추출 규칙을 바꿔도 7일 캐시 때문에 반영 안 됨.** 규칙 수정 후에는 `data/guides.json`을 지우고 스크립트를 다시 실행할 것.
5. 관심 레포는 기기·브라우저별 저장. 시크릿 모드·사이트 데이터 삭제 시 사라짐 (설계상 한계, README에 명시).
6. 링크로 가져온 순위 밖 레포는 설명·스타 정보가 없다 → "트렌딩에 다시 오르면 채워집니다" 문구로 대체.

### 막혔던 지점과 해결
- **원시 10개 안전장치가 매일 실패** → 보충 후 개수 기준으로 변경 (위 결정 참고).
- **첫 봇 커밋 1236줄 diff** (CRLF) → `newline="\n"`.
- **로컬 push가 rejected** (그 사이 봇이 데이터 커밋) → push 전 항상 `git pull --rebase`.
- **모바일에서 카드가 화면보다 넓어짐** → CSS grid 기본 `min-width:auto` 때문. `minmax(0,1fr)` + `section{min-width:0}`.
- **`hidden` 속성이 안 먹음** → `.fav-bar{display:flex}`가 덮어씀. `.fav-bar[hidden]{display:none}` 추가. 새 컴포넌트에 `display`를 줄 때 같은 함정 주의.
- **가이드 파싱 오류들** → 코드블록 안 `# 주석`을 헤딩으로 오인, 디렉터리 트리 줄을 명령으로 오인, 스폰서 영역을 소개문으로 사용, `\` 줄 이어짐을 첫 줄에서 자름 → 모두 `guides.py`에서 수정됨.

### 실패한 접근 / 환경 함정
- **Bash 툴 heredoc에 긴 Python 파일을 넣으면 `unexpected EOF`로 실패.** 파일은 Write 툴로 만들 것. 인라인 `python -c`에서 `'\\'` 같은 백슬래시도 깨짐 → `chr(92)` 등으로 우회하거나 파일로 작성.
- **PowerShell `Get-Content`/`Set-Content`는 한글 UTF-8 파일을 깨뜨림** (다른 프로젝트에서 실제 발생). 파일 수정은 Edit/Write 툴로만.
- `sed`로 Python 문자열 안의 `\n`을 치환하려다 매치 실패 → Edit 툴 사용.
- 브라우저 미리보기 스크린샷이 가끔 5초 타임아웃 → `javascript_tool`/`get_page_text`로 DOM 값 검증으로 대체.
- 미리보기 창 폭이 900px 미만이면 1열 레이아웃이 정상. 2열 확인은 1300px iframe 등으로.

## 5. 실행 · 테스트

```bash
# 수집 (로컬). Windows 콘솔 한글 출력 때문에 PYTHONIOENCODING 필요
PYTHONIOENCODING=utf-8 python scripts/fetch_trending.py

# 미리보기 (file:// 로 열면 fetch가 막혀 오류 화면이 나옴)
python -m http.server 8766        # → http://localhost:8766

# 원격 수동 실행·확인
gh workflow run update.yml -R ojungmin212-dotcom/github-trending-ko
gh run list -R ojungmin212-dotcom/github-trending-ko --workflow=update.yml --limit 5
gh workflow list --all -R ojungmin212-dotcom/github-trending-ko   # active 인지 (disabled_inactivity 주의)
gh api repos/ojungmin212-dotcom/github-trending-ko/pages/builds/latest -q '.status + " " + .commit[0:7]'
```

자동 테스트 스위트는 없다. 검증은 다음으로 한다:
- 스크립트 종료 코드 0 + 로그의 `daily 30개, weekly 30개, monthly 30개`
- 브라우저: 카드 30개, 콘솔 오류 0, 375px에서 가로 넘침 없음(`document.documentElement.scrollWidth <= innerWidth`), 데스크톱(>900px) 2열 + 사이드바
- 푸시 후 Pages 빌드가 해당 커밋으로 `built` 된 뒤 공개 URL에서 변경 확인

### 환경변수 (값은 기록하지 않음)
| 이름 | 용도 | 필수 |
|---|---|---|
| `PYTHONIOENCODING` | `utf-8` — Windows 콘솔 한글 출력 | 로컬 권장 |
| `GITHUB_TOKEN` 또는 `GH_TOKEN` | 가이드의 라이선스·토픽·홈페이지 조회(GitHub API). Actions에서는 `${{ github.token }}` 자동 주입. 로컬에서 없으면 `gh auth token`을 시도하고, 그것도 없으면 해당 항목만 비움 | 선택 |

Actions secret은 쓰지 않는다.

### Git 설정 주의
- 이 머신의 전역 `user.email`은 플레이스홀더라 **저장소 로컬 `user.email`을 저장소 소유 계정 이메일로 설정**해 두었다. 새 클론·새 머신에서도 커밋 전에 로컬 설정을 확인할 것.
- 커밋 메시지는 한국어, `feat:` / `fix:` / `design:` / `data:` 접두사 관례. `data:` 는 봇 전용.

## 6. Claude Code 환경 (MCP · 훅 · 커맨드 · 스킬)

| 종류 | 내용 | 이 프로젝트와의 관계 |
|---|---|---|
| MCP 서버 (settings.json) | 없음 | — |
| 데스크톱 앱 커넥터 | Claude Browser(미리보기·검증), Claude in Chrome, Notion, Claude Docs, visualize 등이 세션에 붙어 있었음 | 미리보기 검증에 **Claude Browser**만 사용. 나머지는 미사용 |
| 훅 | 전역 `~/.claude/settings.json`에 Orca 에이전트 훅(`claude-hook.cmd`)이 모든 이벤트에 걸려 있고 statusLine도 Orca | 머신 전용. 프로젝트 동작과 무관. 새 계정·머신엔 없을 수 있음 |
| 커스텀 커맨드 / 에이전트 | 없음 (`~/.claude/commands`, `agents` 없음) | — |
| 스킬 | 프로젝트 전용 스킬 없음. 세션에서 쓴 것은 내장 기능뿐 | — |
| 미리보기 설정 | `.claude/launch.json` → 이름 `trending`, 포트 8766 | `preview_start name="trending"` |
| 메모리 | 옛 경로 프로젝트 메모리(`C--Users-Win-Desktop-----29-09-23-1/memory/`)에 3개: 한국어 답변 규칙, 프로젝트 운영 메모, 인덱스. **새 경로·새 계정에는 없음** → 핵심 내용은 이 문서와 CLAUDE.md로 옮김 | |

## 7. 참고 (읽기 전용)
- 원본 구현: `C:\Users\Win\Desktop\클로드\26-08-29-3\github-trending\server.py`, `artifact_template.html` — 파싱·번역·초기 디자인의 출처. **절대 수정 금지.** (현재 디자인은 이미 다른 것으로 교체됨)
