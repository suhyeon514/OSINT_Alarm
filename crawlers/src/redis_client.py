import os
import json
import redis

# Docker 네트워크 상의 redis 컨테이너 주소 ("redis")
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

# 연결 풀 생성 (효율적인 연결 관리)
pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0)
r = redis.Redis(connection_pool=pool)

def push_data(source_type, data_dict):
    """
    수집된 데이터를 Redis List('crawling_queue')에 적재합니다.
    :param source_type: 'telegram', 'google', 'twitter' 등 출처 표기
    :param data_dict: 수집한 데이터 본문 (Dictionary)
    """
    payload = {
        "source": source_type,
        "data": data_dict
    }
    try:
        # 리스트의 왼쪽에 데이터 삽입 (LPUSH)
        r.lpush("crawling_queue", json.dumps(payload, ensure_ascii=False))
        print(f"[Redis] Pushed {source_type} data: {str(data_dict)[:50]}...")
    except Exception as e:
        print(f"[Redis Error] {e}")
