FROM python:3.10-slim

WORKDIR /app

#디버깅
ENV PYTHONUNBUFFERED=1

# 1. 필요한 파이썬 라이브러리 설치
# redis: 큐 연결용
# psycopg2-binary: DB 연결용
# requests: 텔레그램 알림용
# google-generativeai: Gemini AI용
RUN pip install redis psycopg2-binary requests google-generativeai

# 2. 소스코드 복사 (호스트의 src 폴더 -> 컨테이너의 /app 폴더)
COPY src/ /app/

# 3. 컨테이너 실행 시 worker.py 가동
CMD ["python", "worker.py"]
