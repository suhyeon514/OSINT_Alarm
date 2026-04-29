import requests
import re
import time
import random
from datetime import datetime
from duckduckgo_search import DDGS  # DuckDuckGo 검색 라이브러리
from dotenv import load_dotenv
import os

# [핵심 변경] Redis Client 임포트
from redis_client import push_data

# ==========================================
# 1. Configuration
# ==========================================
load_dotenv()

# [변경] DB 설정 제거 (크롤러는 DB를 모름)

# Dorks (DuckDuckGo도 구글 문법을 대부분 지원함)
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
    내용에서 위험 패턴을 분석합니다.
    """
    findings = []
    for risk_name, pattern in PATTERNS.items():
        if re.search(pattern, content):
            findings.append(risk_name)
    return findings

# ==========================================
# 3. Main Execution Loop
# ==========================================

def main():
    print("=== Leak Hunter Started (via DuckDuckGo / Redis Mode) ===")
    
    # DDGS 인스턴스 생성
    with DDGS() as ddgs:
        for dork in DORKS:
            print(f"\n[*] Searching Dork: {dork}")
            
            try:
                # DuckDuckGo 검색 실행 (최대 5개)
                results = ddgs.text(dork, max_results=5)
                
                # 결과를 리스트로 변환 (제너레이터일 수 있음)
                results_list = list(results)
                
                if not results_list:
                    print("  [.] No results found for this dork.")
                    continue

                for result in results_list:
                    url = result.get('href')
                    title = result.get('title', 'No Title')
                    snippet = result.get('body', 'No Snippet')

                    if not url: continue

                    print(f"  [-] Visiting: {url[:60]}...")

                    try:
                        # 1. 웹페이지 접속 (Crawl)
                        response = requests.get(url, headers=HEADERS, timeout=10)
                        
                        if response.status_code == 200:
                            content = response.text
                            
                            # 2. 패턴 분석 (Analyze)
                            risks_found = analyze_content(content)
                            
                            # 3. 위험 요소 발견 시 Redis 전송 (Push)
                            if risks_found:
                                print(f"  [!] VULNERABILITY DETECTED: {risks_found}")
                                
                                # [변경] 데이터 구조화
                                payload = {
                                    "title": title,
                                    "link": url,
                                    "snippet": snippet,
                                    "full_content": content[:5000], # 너무 길면 자름
                                    "risk_details": risks_found,
                                    "keyword_used": dork,
                                    "crawled_at": datetime.now().isoformat(),
                                    "has_pii": True
                                }
                                
                                # Redis로 전송 (Source 이름을 'google'로 유지하여 DB 처리가 쉽도록 함)
                                push_data("google", payload)
                                print("  [+] Pushed to Redis!")
                                
                            else:
                                print("  [.] Safe or False Positive")
                                
                        else:
                            print(f"  [x] Connection Failed: Status {response.status_code}")

                    except requests.exceptions.SSLError:
                        print("  [x] SSL Error (Skipping)")
                    except Exception as e:
                        print(f"  [x] Crawling Error: {e}")

                    # 밴 방지 딜레이
                    time.sleep(random.uniform(2, 5))

            except Exception as e:
                print(f"[!] Search Error: {e}")
                continue

    print("\n=== Scan Finished ===")

if __name__ == "__main__":
    main()
