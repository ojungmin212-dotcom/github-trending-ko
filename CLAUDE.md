# CLAUDE.md — 오박사의 GitHub Trending Space

GitHub 트렌딩 Top 30 정적 대시보드. GitHub Actions가 매일 수집해 `data/*.json`을 커밋하고 GitHub Pages가 `index.html`을 호스팅한다.
자세한 맥락·이력·다음 단계는 [HANDOFF.md](HANDOFF.md), 사용자용 설명은 [README.md](README.md).

## 소통
- **모든 답변·보고·질문은 한국어로.** 코드·명령어·경로·해시만 원문 그대로.
- 결정이 필요하면 권장안을 제시하고 진행하되, **공개·외부로 나가는 행위**(새 저장소, 공개 범위 변경, 외부 서비스 연동, 옛 Claude 루틴 끄기 등)는 먼저 확인받는다.

## 절대 원칙
- **Claude API·유료 서비스·외부 Python 패키지 금지.** `scripts/`는 표준 라이브러리만. 새 의존성이 필요해 보이면 먼저 사용자에게 묻는다.
- 원본 참고 폴더 `C:\Users\Win\Desktop\클로드\26-08-29-3\github-trending\`는 **읽기 전용**.
- 안전장치는 "파싱 0개" 또는 "**보충 후** 10개 미만"일 때만 중단. 원시 개수 10개 기준으로 되돌리지 말 것 (GitHub이 daily를 8개만 주는 날이 있어 매일 실패함).
- 디자인은 build.nvidia.com 모방(다크 전용). 사용자가 요청한 것이므로 이전 디자인으로 되돌리지 말 것.
- 관심 레포 localStorage 키 `gtk-favs-v1`과 그 형식을 바꾸면 사용자 저장분이 사라진다 → 바꿀 땐 마이그레이션 코드 필수.

## 코드 컨벤션
- `index.html`은 빌드 없는 단일 파일(CSS·JS 인라인). 프레임워크·번들러 도입 금지.
- 데이터는 **상대 경로**(`data/…`)로 읽고 `?t=Date.now()` 캐시 방지를 붙인다. 절대 경로 `/data/…`는 Pages 하위 경로(`/github-trending-ko/`)에서 깨진다.
- 사용자 입력·외부 데이터를 HTML에 넣을 때는 반드시 `esc()`.
- 색은 `:root` CSS 변수(`--green #76b900`, `--panel #161616` 등)만 사용.
- `display`를 지정한 요소에 `hidden` 속성을 쓰면 무시된다 → `.x[hidden]{display:none}`을 함께 둔다.
- 그리드·플렉스 자식에는 `min-width:0` / `minmax(0,1fr)`. 빠뜨리면 모바일에서 가로 넘침이 생긴다.
- JSON 저장은 `write_json()`(UTF-8, `newline="\n"`, 임시 파일 후 교체)만 사용.
- 주석·커밋 메시지는 한국어. 커밋 접두사 `feat:` `fix:` `design:` `docs:` / `data:`는 Actions 봇 전용.

## Windows 환경 함정
- 파일 생성·수정은 **Edit/Write 툴로만.** PowerShell `Get-Content`/`Set-Content`는 한글 UTF-8을 깨뜨린다.
- Bash 툴 heredoc에 긴 Python 코드를 넣으면 `unexpected EOF`로 실패하는 일이 있다 → 파일로 작성 후 실행.
- 스크립트 실행 시 `PYTHONIOENCODING=utf-8`.

## 작업 흐름
1. 시작 전 `git pull --rebase` — Actions 봇이 매일 `data/` 커밋을 만든다. push 전에도 다시 rebase.
2. 수집 로직 변경 → `PYTHONIOENCODING=utf-8 python scripts/fetch_trending.py`로 세 기간 30개 확인.
   가이드 추출 규칙 변경 → `data/guides.json`을 지우고 재실행(7일 캐시 때문에 안 바뀜).
3. 화면 변경 → `python -m http.server 8766`(`.claude/launch.json`의 `trending`)으로 확인:
   카드 30개, 콘솔 오류 0, 375px에서 `scrollWidth <= innerWidth`, 900px 초과에서 2열 + 사이드바.
4. 커밋·푸시 후 `gh api repos/ojungmin212-dotcom/github-trending-ko/pages/builds/latest`가 해당 커밋으로 `built` 된 것을 보고 공개 URL에서 확인.
5. 커밋 전 로컬 `git config user.email`이 저장소 소유 계정 이메일인지 확인(전역 값은 플레이스홀더).
