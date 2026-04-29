import asyncio
from playwright.async_api import async_playwright
import re
import random
from datetime import datetime
import os
from dotenv import load_dotenv
# [변경 1] Redis Client 임포트
from redis_client import push_data

# ==========================================
# 1. Configuration & Targets
# ==========================================
TARGET_ACCOUNTS = [
    "DarkWebInformer", 
    "FalconFeedsio", 
    "DailyDarkWeb", 
    "vxunderground",
    "H4ckManac",       
    "SOSIntel"         
]

load_dotenv()

# [변경 2] DB 설정 제거 (크롤러는 DB 정보를 모름)

# ==========================================
# 2. Helper Functions
# ==========================================
def extract_signals(text):
    """Extract URLs and Hashtags from text"""
    url_pattern = r'(https?://[^\s]+)'
    links = re.findall(url_pattern, text)
    
    hashtag_pattern = r'(#\w+)'
    hashtags = re.findall(hashtag_pattern, text)
    
    return links, hashtags

async def human_scroll(page):
    """Scroll smoothly like a human"""
    for _ in range(random.randint(2, 4)): 
        scroll_amount = random.randint(300, 700)
        await page.mouse.wheel(0, scroll_amount)
        await page.wait_for_timeout(random.randint(1000, 3000))

# ==========================================
# 3. Main Logic
# ==========================================
async def run():
    async with async_playwright() as p:
        # Browser Launch Options
        # Docker 환경에서는 --no-sandbox 등이 필수입니다.
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox", 
                "--disable-setuid-sandbox", 
                "--disable-dev-shm-usage",
                "--disable-gpu", 
                "--disable-blink-features=AutomationControlled"
            ]
        )
        
        # 세션 파일 경로 (Docker 볼륨 마운트 경로로 지정 권장)
        # auth 파일이 없으면 로그인이 안 된 상태로 진행됩니다 (공개 프로필은 보일 수 있음)
        auth_file = "twitter_auth.json"
        
        if os.path.exists(auth_file):
            context = await browser.new_context(
                storage_state=auth_file,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-US"
            )
            print(f"[Info] Loaded session from {auth_file}")
        else:
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-US"
            )
            print("[Info] No session file found. Running anonymously.")
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        page = await context.new_page()

        print("[Start] Starting Twitter crawler (Redis Mode)...\n")

        for target in TARGET_ACCOUNTS:
            print(f"[Target] Accessing {target}...")
            
            try:
                await page.goto(f"https://twitter.com/{target}", timeout=60000)
                
                wait_time = random.uniform(3, 6)
                await page.wait_for_timeout(wait_time * 1000)
                
                try:
                    await page.wait_for_selector("article", timeout=15000)
                except:
                    print(f"   [Skip] Failed to load {target} or no tweets found.")
                    continue

                await human_scroll(page)

                tweets = await page.query_selector_all("article")
                print(f"   [Found] {len(tweets)} tweets found.")

                saved_count = 0
                for tweet in tweets:
                    try:
                        text_el = await tweet.query_selector('div[data-testid="tweetText"]')
                        if not text_el: continue
                        content = await text_el.inner_text()
                        
                        time_el = await tweet.query_selector('time')
                        post_date = await time_el.get_attribute('datetime') if time_el else datetime.now().isoformat()
                        
                        links, tags = extract_signals(content)
                        temp_id = f"{target}_{post_date}"

                        # [변경 3] 데이터 구조화 (JSON으로 보낼 준비)
                        data_payload = {
                            "tweet_id": temp_id,
                            "author": target,
                            "content": content,
                            "external_links": links,
                            "hashtags": tags,
                            "post_date": post_date,
                            "collected_at": datetime.now().isoformat()
                        }

                        # [변경 4] DB Insert 대신 Redis Push
                        push_data("twitter", data_payload)
                        saved_count += 1
                        
                    except Exception as e:
                        continue
                
                print(f"   [Pushed] {saved_count} tweets sent to Redis.")
                
                rest_time = random.uniform(5, 10)
                await page.wait_for_timeout(rest_time * 1000)

            except Exception as e:
                print(f"   [Error] Error crawling {target}: {e}")

        await browser.close()
        print("[Done] Crawler cycle finished.")

if __name__ == "__main__":
    asyncio.run(run())
