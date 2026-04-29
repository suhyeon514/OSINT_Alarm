import json
import time
import hashlib
import redis
import config
import database as db
import extractor   
import ai_agent    
import notifier
import sys
import traceback

# [디버깅] 코드 진입 확인용
print("🔥🔥🔥 [DEBUG] worker.py 파일 로드됨 (v2.1 트위터 해결판) 🔥🔥🔥", flush=True)

def main():
    print("🔥🔥🔥 [DEBUG] main 함수 진입 🔥🔥🔥", flush=True)
    
    # 1. Redis 연결
    r = None
    while True:
        try:
            print(f"🔥🔥🔥 [DEBUG] Redis 접속 시도 중... (Host: {config.REDIS_HOST})", flush=True)
            r = redis.Redis(host=config.REDIS_HOST, port=6379, db=0)
            r.ping() 
            print("[*] Worker: Redis 연결 성공! 시스템 가동. 데이터 대기 중...", flush=True)
            break 
        except redis.ConnectionError as e:
            print(f"[!] Redis 연결 실패: {e}", flush=True)
            time.sleep(5)
        except Exception as e:
            print(f"[!] Redis 연결 중 알 수 없는 에러: {e}", flush=True)
            time.sleep(5)

    # 2. 데이터 처리 루프
    while True:
        try:
            item = r.blpop("crawling_queue", timeout=30)
            if not item: continue 
            
            _, json_data = item
            try:
                data = json.loads(json_data)
            except json.JSONDecodeError:
                print(f"[!] JSON 파싱 에러: {json_data}", flush=True)
                continue

            # ========================================================
            # [핵심 수정] 중첩된 'data' 딕셔너리 평탄화 (Flatten)
            # 트위터 크롤러처럼 {'data': {'content':...}} 구조일 경우
            # 안쪽 데이터를 바깥으로 꺼내서 합쳐줍니다.
            # ========================================================
            if "data" in data and isinstance(data["data"], dict):
                inner_data = data["data"]
                # 안쪽 데이터를 바깥쪽 data에 합침 (기존 키 덮어쓰지 않음)
                for k, v in inner_data.items():
                    if k not in data:
                        data[k] = v
            # ========================================================

            source = data.get("source", "unknown")
            
            # 키 목록 확인 (이제 'content'가 보일 것입니다)
            print(f"🔥🔥 [DEBUG] {source} 데이터 키 목록: {list(data.keys())}", flush=True)

            content_candidates = [
                "content", "full_content", "text",  # 기본
                "description", "readme", "body",    # GitHub
                "message", "caption",               # Telegram
                "tweet", "full_text"                # Twitter
            ]
            
            content = ""
            found_key = ""
            
            for key in content_candidates:
                val = data.get(key)
                if val and isinstance(val, str) and len(val.strip()) > 0:
                    content = val
                    found_key = key
                    break 
            
            # URL도 마찬가지로 합쳐진 data에서 찾음
            url = data.get("url") or data.get("link") or data.get("external_link") or ""

            if not content: 
                print(f"[-] 내용 없음 스킵: {source}", flush=True)
                continue
            
            print(f"[+] 본문 추출 성공 ({found_key}): {content[:50].replace(chr(10), ' ')}...", flush=True)

            # [DB 연결]
            conn = db.get_conn()
            if not conn: 
                print("[!] DB 연결 실패, 재시도...", flush=True)
                time.sleep(1)
                continue

            # [중복 체크]
            unique_key = url if url else hashlib.md5((content + str(data.get("post_date",""))).encode()).hexdigest()
            
            if db.is_duplicate(conn, unique_key):
                print(f"[-] 중복 데이터 스킵: {source}", flush=True)
                conn.close()
                continue

            # [분석 단계]
            extracted_tags = extractor.extract_all(content)
            keywords = db.get_keywords(conn)
            matched = [k for k in keywords if k.lower() in content.lower()]
            
            llm_summary = ""
            risk_level = "LOW"
            
            if matched:
                print(f"[!] 🚨 위험 감지됨 (키워드: {matched})", flush=True)
                llm_summary, risk_level = ai_agent.analyze_risk(content, matched)
                notifier.send_telegram(source, matched, risk_level, llm_summary, url, data.get("file_hash"))

            # [DB 저장]
            data_pack = {
                "source": source,
                "raw_data": data, # 합쳐진 데이터를 통째로 저장
                "unique_key": unique_key,
                "extracted": extracted_tags,
                "matched": matched,
                "llm_summary": llm_summary,
                "risk_level": risk_level
            }
            
            if db.save_data(conn, data_pack):
                print(f"[+] DB 저장 완료: {source} (Risk: {risk_level})", flush=True)
            else:
                print(f"[!] DB 저장 실패: {source}", flush=True)

            conn.close()

        except Exception as e:
            print(f"[Error] 처리 중 에러: {e}", flush=True)
            traceback.print_exc()
            time.sleep(1)

if __name__ == "__main__":
    main()
