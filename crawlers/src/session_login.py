import os
from dotenv import load_dotenv
from telethon import TelegramClient

# 1) 환경변수 로드
load_dotenv() 

# docker-compose.yml에서 주입된 환경변수 사용
api_id = os.environ.get("TG_API_ID")
api_hash = os.environ.get("TG_API_HASH")

if not api_id or not api_hash:
    print("❌ 오류: TG_API_ID 또는 TG_API_HASH 환경변수가 없습니다.")
    exit(1)

api_id = int(api_id)

# ✅ 세션 저장 경로 (Docker 볼륨과 연결된 경로)
# docker-compose에서 TG_SESSION_PATH=/app/sessions/anon 으로 설정했음
SESSION_PATH = os.environ.get("TG_SESSION_PATH", "/app/sessions/anon")

print(f"[*] 세션 생성 시작... 경로: {SESSION_PATH}")

# 2) 클라이언트 생성
client = TelegramClient(SESSION_PATH, api_id, api_hash)

async def main():
    # ✅ 대화형 로그인 트리거 (여기서 폰번호 입력 대기함)
    await client.start()
    
    me = await client.get_me()
    print(f"\n✅ 로그인 성공! 계정: {me.username} (ID: {me.id})")
    print(f"✅ 세션 파일이 '{SESSION_PATH}.session'에 저장되었습니다.")

    # 테스트 메시지 (나에게)
    await client.send_message("me", "✅ 다크웹 모니터링 시스템: 세션 연결 성공!")

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
