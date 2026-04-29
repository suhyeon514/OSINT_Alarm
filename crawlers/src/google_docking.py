import requests
import re
import time
import random
import sys
from datetime import datetime
from googlesearch import search # requirements.txt에 추가 필요
from dotenv import load_dotenv

# [변경 1] Redis Client 임포트
from redis_client import push_data

# ==========================================
# 1. Configuration
# ==========================================

load_dotenv()

# [변경 2] DB 설정 제거 (크롤러는 DB를 모름)

# Google Dorks
DORKS = [
    'site:pastebin.com "password" "gmail.com"',
    'ext:env "DB_PASSWORD" -git',
    'ext:log "password" "username" -git',
    'filetype:xls "password" OR "credential"',
    'intext:"BEGIN RSA PRIVATE KEY" ext:pem'
]

# Regex Patterns
PATTERNS = {
    "AWS_ACCESS_KEY": r'AKIA[0-9A-Z]{16}',
    "RRN_KOREA": r'\d{6}[-][1-4]\d{6}',
    "EMAIL_PASS_COMBO": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\s*[:]\s*\S+',
    "GENERIC_API_KEY": r'(api_key|apikey|secret|token)\s*[:=]\s*["\'][a-zA-Z0-9]{20,}["\']'
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# ==========================================
# 2. Helper Functions
# ==========================================

def analyze_content(content):
    """
    정규식으로 위험 패턴을 분석합니다.
    """
    findings = []
    for risk_name, pattern in PATTERNS.items():
        if re.search(pattern, content):
            findings.append(risk_name)
    return findings

# [변경 3] DB 저장 함수 -> Redis Push 함수로 변경
def push_to_redis(title, url, snippet, content, findings, dork):
    """
    위험 데이터가 확인되면 Redis 큐로 전송합니다.
    """
    # JSON 구조화
    payload = {
        "title": title,
        "link": url,
        "snippet": snippet or "Collected via generic dorking",
        "full_content": content[:5000], # 너무 긴 내용은 잘라서 전송 (선택사항)
        "risk_details": findings,       # 리스트 형태
        "keyword_used": dork,
        "crawled_at": datetime.now().isoformat(),
        "has_pii": True
    }
    
    # Redis로 전송
    push_data("google", payload)
    
    risk_summary = ", ".join(findings)
    print(f"  [+] Pushed to Redis! ({risk_summary})")

# ==========================================
# 3. Main Execution Loop
# ==========================================

def main():
    print("=== Google Leak Hunter Started (Redis Mode) ===")
    
    # 무한 루프가 필요하다면 while True 추가 가능, 여기선 1회성 실행으로 유지
    for dork in DORKS:
        print(f"\n[*] Searching Dork: {dork}")
        
        try:
            # 1. Perform Google Search
            # num_results는 테스트를 위해 작게 설정하는 것이 좋습니다.
            search_iterator = search(dork, num_results=5)
            
            urls = []
            try:
                urls = list(search_iterator)
            except Exception as e:
                print(f"  [!] Error fetching results (Blocked?): {e}")

            if not urls:
                print("  [!] No results found (0 items).")
                continue

            # 2. Crawl and Analyze
            for url in urls:
                print(f"  [-] Visiting: {url[:60]}...")
                title = "Unknown (Fetched via URL)"
                
                try:
                    response = requests.get(url, headers=HEADERS, timeout=10)
                    
                    if response.status_code == 200:
                        content = response.text
                        
                        # Analyze content
                        risks_found = analyze_content(content)
                        
                        # Save if risky
                        if risks_found:
                            print(f"  [!] VULNERABILITY DETECTED: {risks_found}")
                            # [변경 4] Redis 전송 함수 호출
                            push_to_redis(title, url, None, content, risks_found, dork)
                        else:
                            print("  [.] Safe or False Positive")
                    else:
                        print(f"  [x] Connection Failed: Status {response.status_code}")

                except requests.exceptions.SSLError:
                    print("  [x] SSL Error (Skipping)")
                except Exception as e:
                    print(f"  [x] Crawling Error: {e}")

                # 구글 밴 방지를 위한 지연 시간
                time.sleep(random.uniform(3, 7))

        except Exception as e:
            print(f"[!] Fatal Error in Dork loop: {e}")
            break 

    print("\n=== Scan Finished ===")

if __name__ == "__main__":
    main()
