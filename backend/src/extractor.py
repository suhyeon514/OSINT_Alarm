import re

# === 마스킹 함수 ===
def mask_rrn(match):
    s = match.group()
    return (s[:8] + "******") if '-' in s else (s[:7] + "*******")

def mask_card(match):
    s = match.group()
    return s[:4] + "-****-****-" + s[-4:]

# === 정규식 패턴 ===
PATTERNS = {
    "email": (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", None),
    "ip": (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", None),
    "onion": (r"[a-z2-7]{16,56}\.onion", None),
    "rrn": (r"\b\d{6}[- ]?[1-4]\d{6}\b", mask_rrn),
    "credit_card": (r"\b(?:\d{4}[- ]?){3}\d{4}\b", mask_card),
    "btc_wallet": (r"\b(1|3|bc1)[a-zA-Z0-9]{25,39}\b", None)
}

def extract_all(content):
    """텍스트에서 핵심 정보 추출"""
    extracted = {}
    for key, (pattern, mask_func) in PATTERNS.items():
        matches = list(set(re.findall(pattern, content)))
        if matches:
            if mask_func:
                extracted[key] = [mask_func(re.search(pattern, m)) for m in matches]
            else:
                extracted[key] = matches
    return extracted
