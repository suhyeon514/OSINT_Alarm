# OSINT_Alarm (OSINT 기반 유출/위험 징후 알림 시스템)

다크웹/온라인 채널(텔레그램, 트위터, GitHub 등)에서 유출 징후를 수집하고,
등록된 키워드와 매칭되면 LLM으로 위험도를 분석한 뒤 텔레그램으로 알림을 보내는 시스템입니다.

### 핵심 구성요소

- **Redis**: 크롤러 → 워커 데이터 전달을 위한 메시지 큐
- **PostgreSQL**: 탐지 결과/원문/요약/위험도 저장
- **crawlers/**: 데이터 수집기(텔레그램/트위터/GitHub 등)
- **backend/**: Redis에서 데이터를 소비하고 분석/저장/알림하는 워커

---

### 아키텍처 / 데이터 흐름

1. 크롤러(crawlers)가 외부 소스에서 게시글/코드 등을 수집
2. 크롤러가 수집 데이터를 **Redis 리스트(큐)** 로 push  
3. backend 워커가 Redis에서 pop하여 처리:
   - 본문(content) 추출
   - 키워드 매칭
   - LLM(Gemini)로 요약 및 위험도(risk_level) 산정
   - 텔레그램으로 경고 메시지 전송
   - PostgreSQL에 결과 저장

---

### 사전 요구사항

- Docker / Docker Compose
- (텔레그램 크롤링 사용 시) Telegram API ID / HASH
- (GitHub 스캐너 사용 시) GitHub Personal Access Token
- (AI 요약/위험도 분석 사용 시) Gemini API Key
- (알림 사용 시) Telegram Bot Token / Chat ID

---

### 빠른 시작(도커로 전체 구동)

**1) 환경변수 준비 (.env 권장)**

레포 루트에 `.env` 파일을 만들고 아래 값을 채우세요.

> **주의**: 토큰/키/세션 파일은 절대 Git에 커밋하지 마세요.

예시:

```bash
# GitHub
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Telegram (Telethon)
TG_API_ID=123456
TG_API_HASH=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TG_SESSION_PATH=/app/sessions/anon

# Telegram 알림(봇)
TG_BOT_TOKEN=123456789:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TG_CHAT_ID=123456789

# Gemini
GEMINI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Postgres (옵션: docker-compose에 이미 값이 있을 수 있으나, 운영에서는 반드시 변경 권장)
POSTGRES_USER=phoenix
POSTGRES_PASSWORD=change_me
POSTGRES_DB=darkweb_project
```

**2) 텔레그램 모니터링 대상 채널 설정**

`crawlers/src/channel_name.txt`에 모니터링할 채널을 등록합니다.

형식(예):
- `<표시이름> <채널ID(-100로 시작하는 숫자)>`

예:
```
Some Channel -1001234567890
Another Channel -1009876543210
```

> 운영/보안상 이 파일은 민감할 수 있으니 공개 저장소에서는 비공개 처리 또는 샘플 파일로 분리하는 것을 권장합니다.

**3) (선택) 텔레그램 세션 생성 (로그인)**

텔레그램 크롤러가 계정으로 채널에 접근해야 하는 경우, 세션 파일이 필요할 수 있습니다.
`crawlers/src/session_login.py`는 Telethon 세션을 생성하는 스크립트입니다.

- Docker 환경에서 실행하여 세션 파일을 `./tg_sessions` 볼륨에 저장하도록 구성되어 있습니다.
- 실행 후 콘솔 안내에 따라 전화번호/인증코드를 입력합니다.

> 세션 파일(`*.session`)은 계정 접근 권한이 될 수 있으므로 절대 공유/커밋하지 마세요.

**4) 도커 컴포즈 실행**

```bash
docker compose up -d --build
```

컨테이너:
- `darkweb_redis` (redis)
- `darkweb_db` (postgres)
- `crawler_group` (크롤러 컨테이너, 기본적으로 명령이 `tail -f /dev/null`이라 내부에서 스크립트를 수동 실행하는 구조일 수 있음)
- `backend_worker` (Redis 소비/분석/알림/저장)

---

### 크롤러 실행 방법(예시)

현재 compose 설정상 `crawler_group`은 대기 상태(`tail -f /dev/null`)로 뜨므로,
컨테이너 내부에서 필요한 크롤러를 실행하는 방식으로 사용할 수 있습니다.

```bash
docker exec -it crawler_group bash
```

컨테이너 안에서 예:
- 텔레그램 크롤러:
  ```bash
  python telegram_crawler.py
  ```
- GitHub 스캐너:
  ```bash
  python github_crawler.py
  ```
- 트위터 크롤러:
  ```bash
  python twitter_crawler.py
  ```

---

### 백엔드 워커 동작(무엇을 하는가)

`backend_worker`는 Redis의 `crawling_queue`를 블로킹 pop 하며 데이터를 처리합니다.

처리 요약:
- 본문 필드 후보(content/full_content/text/description 등)에서 텍스트를 찾음
- DB 중복 체크(링크 또는 content+날짜 기반)
- 키워드 매칭
- 매칭 시 Gemini로 위험도 분석 + 텔레그램 알림 전송
- 결과를 PostgreSQL에 저장

---

### 보안 주의사항(필수)

- `docker-compose.yml`에 기본 DB 비밀번호가 `password`로 들어있을 수 있습니다. 운영에서는 반드시 변경하세요.
- `.env`, `twitter_auth.json`, `*.session`(텔레그램), 토큰/키는 절대 커밋 금지
- `crawlers/src/channel_name.txt`는 운영상 민감할 수 있으므로 샘플 파일로 분리 권장
- 외부에서 접근 가능한 Redis/Postgres 포트(6379, 5432)를 그대로 열면 위험할 수 있습니다(방화벽/네트워크 제한 권장)

---

## 문제 해결(간단 체크)

- Redis 연결 실패:
  - `REDIS_HOST`가 컨테이너 이름(`darkweb_redis`)으로 설정되어 있는지 확인
- 텔레그램 크롤러 실행 오류:
  - `TG_API_ID`, `TG_API_HASH` 설정 확인
  - 필요한 채널에 계정이 참여/접근 가능한지 확인
- GitHub 스캐너 403/429:
  - 토큰 권한/Rate limit 확인, 대기 후 재시도