import os
import random
import asyncio
import hashlib  # [추가] 해시 계산용
from zoneinfo import ZoneInfo
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
import socks
from redis_client import push_data

# 한국 시간 설정
KST = ZoneInfo("Asia/Seoul")

# ============== [설정 로드] ==============
CHANNEL_NAME_FILE = "channel_name.txt"
api_id = int(os.environ["TG_API_ID"])
api_hash = os.environ["TG_API_HASH"]

CRAWL_MODE = os.environ.get("CRAWL_MODE", "event").strip().lower()
RECENT_MESSAGE_LIMIT_AT_FIRST = int(os.environ.get("RECENT_MESSAGE_LIMIT_AT_FIRST", "10"))
SESSION_PATH = os.environ.get("TG_SESSION_PATH", "/app/sessions/anon")

# ============== [프록시 설정] ==============
def parse_proxies(env_value: str):
    proxies = []
    if not env_value:
        return proxies
    for item in env_value.split(","):
        parts = item.split(":")
        if len(parts) == 2:
            proxies.append(dict(proxy_type=socks.SOCKS5, addr=parts[0], port=int(parts[1]), rdns=True))
        elif len(parts) == 4:
            proxies.append(dict(proxy_type=socks.SOCKS5, addr=parts[0], port=int(parts[1]),
                                username=parts[2], password=parts[3], rdns=True))
    return proxies

PROXY_LIST = parse_proxies(os.environ.get("TG_PROXIES", ""))
proxy = random.choice(PROXY_LIST) if PROXY_LIST else None

if proxy:
    print(f"[INFO] Proxy 적용: {proxy['addr']}:{proxy['port']}")
    client = TelegramClient(SESSION_PATH, api_id, api_hash, proxy=proxy)
else:
    client = TelegramClient(SESSION_PATH, api_id, api_hash)

# ============== [유틸리티 함수] ==============
def load_channel_targets(path: str):
    """채널 목록 파일 로드 (-100... ID 파싱)"""
    target_ids = set()
    id_to_label = {}

    if not os.path.exists(path):
        return target_ids, id_to_label

    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "#" in line:
                line = line.split("#", 1)[0].strip()
                if not line: continue

            parts = line.split()
            if not parts: continue

            last = parts[-1]
            if last.startswith("-100") and last.lstrip("-").isdigit():
                cid = int(last)
                label = line[: line.rfind(last)].strip() or str(cid)
                target_ids.add(cid)
                id_to_label[cid] = label
            else:
                print(f"[WARN] ID 형식 오류 무시: {raw.rstrip()!r}")

    return target_ids, id_to_label

def calculate_sha256(file_path):
    """파일의 SHA-256 해시값을 계산"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # 메모리 효율을 위해 4KB씩 읽음
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

# ============== [핵심: 데이터 처리 및 저장] ==============
async def process_and_save(channel_id: int, channel_name: str, message):
    if not message:
        return

    msg_id = int(message.id)
    text = message.message or ""
    # 날짜가 없으면 현재 시간으로 대체 (가끔 날짜 없는 시스템 메시지 대비)
    if message.date:
        post_date = message.date.astimezone(KST).isoformat()
    else:
        post_date = ""

    # --- [파일 해시 처리 로직] ---
    file_hash = None
    file_name = None
    has_file = bool(message.media)

    if has_file:
        try:
            # 1. 임시 폴더 생성
            temp_dir = "temp_downloads"
            os.makedirs(temp_dir, exist_ok=True)
            
            # 2. 다운로드 (파일명 충돌 방지)
            filename_prefix = f"{channel_id}_{msg_id}"
            path = await message.download_media(file=f"{temp_dir}/{filename_prefix}")
            
            if path:
                # 3. 해시 계산 및 파일명 확보
                file_hash = calculate_sha256(path)
                file_name = os.path.basename(path)
                
                # 4. 파일 즉시 삭제 (보안 및 용량 관리)
                os.remove(path)
        except Exception as e:
            print(f"[WARN] 미디어 처리 실패 (Skip): {e}")
            # 파일 처리에 실패해도 텍스트는 수집하도록 에러는 무시

    # Redis 전송 데이터 구성
    data = {
        "channel_id": channel_id,
        "channel_name": channel_name,
        "message_id": msg_id,
        "content": text,
        "post_date": post_date,
        "has_file": has_file,
        "file_hash": file_hash,  # 해시값 (없으면 None)
        "file_name": file_name   # 파일명 (없으면 None)
    }

    # Redis 큐로 전송
    push_data("telegram", data)

# ============== [초기 수집 및 메인 루프] ==============
async def initial_sync(found_by_id, id_to_label, limit: int):
    print(f"\n[INFO] 초기 수집 시작: 채널당 최근 {limit}개")
    for cid, dialog in found_by_id.items():
        cname = id_to_label.get(cid, dialog.name or str(cid))
        try:
            msgs = await client.get_messages(dialog.entity, limit=limit)
            for m in reversed(msgs):
                await process_and_save(int(dialog.id), cname, m)
        except FloodWaitError as e:
            print(f"[WAIT] 텔레그램 요청 제한. {e.seconds}초 대기...")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"[ERR] 초기 수집 중 오류 ({cname}): {e}")

async def main():
    target_ids, id_to_label = load_channel_targets(CHANNEL_NAME_FILE)

    print("\n[DEBUG] 모니터링 대상 채널:")
    for x in sorted(target_ids):
        print(f" - [{x}] {id_to_label.get(x)}")

    if not target_ids:
        print("[WARN] 대상 채널이 없습니다. channel_name.txt를 확인하세요.")
        return

    found_by_id = {}
    print("\n[INFO] 대화 목록 스캔 중...")
    
    # 내 계정이 참여 중인 방 목록 가져오기
    async for dialog in client.iter_dialogs(limit=None):
        did = int(dialog.id)
        if did in target_ids:
            found_by_id[did] = dialog
            print(f"[HIT] 참여 확인됨: {dialog.name} ({did})")

    missing = sorted(list(target_ids - set(found_by_id.keys())))
    if missing:
        print(f"[WARN] 미참여 또는 접근 불가 채널 ID: {missing}")

    # 1. 초기 데이터 수집
    await initial_sync(found_by_id, id_to_label, RECENT_MESSAGE_LIMIT_AT_FIRST)

    # 2. 실시간 감시 (Event Mode)
    if CRAWL_MODE == "event":
        print("[INFO] 텔레그램 실시간 감시 모드 시작 (Ctrl+C로 종료)...")
        
        # 감시할 채팅방 엔티티 리스트
        chat_entities = [d.entity for d in found_by_id.values()]
        
        @client.on(events.NewMessage(chats=chat_entities))
        async def handler(event):
            cid = int(event.chat_id)
            cname = id_to_label.get(cid, str(cid))
            await process_and_save(cid, cname, event.message)
            # 로그 출력 (선택 사항)
            print(f"[NEW] {cname}: {event.message.text[:30]}...")

        await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
