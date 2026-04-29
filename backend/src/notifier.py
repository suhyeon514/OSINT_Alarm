import requests
import config

def send_telegram(source, matched, risk_level, summary, url=None, file_hash=None):
    if not config.TG_BOT_TOKEN or not config.TG_CHAT_ID:
        return

    msg = f"🚨 *[경고] {source.upper()} 탐지*\n\n"
    msg += f"🔑 *매칭*: `{', '.join(matched)}`\n"
    msg += f"🧠 *위험도*: {risk_level}\n"
    msg += f"📝 *요약*: {summary}\n"
    if url: msg += f"🔗 *링크*: {url}\n"
    if file_hash: msg += f"📂 *파일해시*: `{file_hash}`"

    try:
        url = f"https://api.telegram.org/bot{config.TG_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": config.TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[!] 알림 전송 실패: {e}")
