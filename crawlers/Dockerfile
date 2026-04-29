# 1. 베이스 이미지 (가벼운 파이썬 버전)
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 2. 시스템 패키지 설치
# - gcc, libpq-dev: DB 연결 라이브러리(psycopg2) 설치용
# - curl: 다운로드용 도구
# - Playwright 의존성: 브라우저 실행에 필요한 시스템 라이브러리들
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. 파이썬 라이브러리 설치 (requirements.txt 먼저 복사)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Playwright 브라우저 설치 (트위터 크롤러용)
# Chromium 브라우저와 관련 의존성을 설치합니다.
RUN playwright install --with-deps chromium

# 5. 소스코드 복사 (호스트의 src 폴더 -> 컨테이너 /app)
COPY src/ /app/

# 6. 데이터 저장용 폴더 생성
RUN mkdir -p /app/sessions /app/downloads

# 7. 컨테이너 실행 명령 (기본은 대기 상태 유지)
CMD ["tail", "-f", "/dev/null"]
