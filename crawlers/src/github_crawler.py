import time
import requests
from datetime import datetime
from dotenv import load_dotenv
import os
# [변경 1] Redis Client 임포트
from redis_client import push_data

# ==========================================
# 1. Configuration
# ==========================================
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

SEARCH_KEYWORDS = [
    # 1. Whole File Leaks (High Probability)
    "filename:.env DB_HOST",
    "filename:.npmrc _auth",
    "filename:docker-compose.yml POSTGRES_PASSWORD",

    # 2. Key Patterns
    "AKIAIO JP",
    "sk_live_",
    "xoxb-",
    "-----BEGIN RSA PRIVATE KEY-----",

    # 3. Korean Ecosystem Targets
    "serviceKey filename:config.js",
    "imp_key filename:server",
    "coolsms_api_key",
    "naver_client_secret filename:properties",
    "kakao_admin_key"
]

# [변경 2] DB 설정 제거

# ==========================================
# 2. Main Logic
# ==========================================
def scan_github_final():
    if not GITHUB_TOKEN:
        print("[Fatal] GITHUB_TOKEN is missing in .env")
        return

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    print("[*] Starting GitHub Scanner (Redis Mode)...\n")

    for keyword in SEARCH_KEYWORDS:
        try:
            print(f"[Search] Query: '{keyword}'")
            
            # API Request
            url = "https://api.github.com/search/code"
            params = { "q": keyword, "sort": "indexed", "order": "desc", "per_page": 10 }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code in [403, 429]:
                print(f"[!] Rate Limit! Waiting 60s...")
                time.sleep(60)
                continue
            elif response.status_code != 200:
                print(f"[!] API Error: {response.status_code}")
                continue

            items = response.json().get("items", [])
            print(f"   L Found {len(items)} items.")

            for item in items:
                try:
                    repo_name = item["repository"]["full_name"]
                    file_path = item["path"]
                    html_url = item["html_url"]
                    
                    # [변경 3] 중복 체크 제거 (Worker가 DB 저장 시 처리함)
                    
                    # Fetch Raw Content
                    # Convert HTML URL to Raw URL
                    raw_url = item.get("html_url").replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                    code_res = requests.get(raw_url, timeout=5)
                    
                    if code_res.status_code != 200:
                        print(f"   [Skip] Failed to fetch raw content: {repo_name}")
                        continue
                        
                    full_content = code_res.text
                    snippet = full_content[:1000] # 미리보기용

                    # [변경 4] 데이터 구조화 및 Redis 전송
                    payload = {
                        "keyword": keyword,
                        "repo_name": repo_name,
                        "file_path": file_path,
                        "file_url": html_url,
                        "code_snippet": snippet,
                        "full_content": full_content, # 전체 코드 저장 (필요 시)
                        "author_id": item["repository"]["owner"]["login"],
                        "crawled_at": datetime.now().isoformat()
                    }
                    
                    push_data("github", payload)
                    
                    print(f"   [+] Pushed to Redis: {repo_name}")
                    time.sleep(1)

                except Exception as file_e:
                    print(f"   [-] Processing Error: {file_e}")
                    time.sleep(1)

            print(f"   L Resting 5 seconds...\n")
            time.sleep(5)

        except Exception as e:
            print(f"[Error] {e}")
            time.sleep(5)

    print("\n[Done] Scan completed.")

if __name__ == "__main__":
    scan_github_final()
