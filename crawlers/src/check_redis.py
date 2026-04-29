import redis
import json
from collections import Counter
import os

# 1. Redis 연결 (Docker 내부 주소 사용)
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

# 2. 큐 이름
QUEUE_NAME = "crawling_queue"

def check_queue_stats():
    # 전체 길이 확인
    total_count = r.llen(QUEUE_NAME)
    
    if total_count == 0:
        print("\n[!] Redis 큐가 비어있습니다.")
        return

    print(f"\n=== Redis Queue Status (Total: {total_count}) ===")
    
    # 3. 데이터 전체 조회 (꺼내지 않고 조회만: lrange 0 -1)
    all_items = r.lrange(QUEUE_NAME, 0, -1)
    
    # 4. 소스별 카운팅
    stats = Counter()
    
    for item in all_items:
        try:
            # JSON 파싱
            data_str = item.decode('utf-8')
            data_json = json.loads(data_str)
            
            # source 필드 확인 (google, github, twitter 등)
            source = data_json.get("source", "unknown")
            stats[source] += 1
            
        except Exception:
            stats["corrupted_data"] += 1

    # 5. 결과 출력
    for source, count in stats.items():
        print(f" - {source.ljust(10)} : {count} 개")
    print("=========================================\n")

if __name__ == "__main__":
    try:
        check_queue_stats()
    except Exception as e:
        print(f"[Error] Redis 연결 실패: {e}")
