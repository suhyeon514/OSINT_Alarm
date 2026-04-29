import google.generativeai as genai
import config

if config.GEMINI_API_KEY:
    genai.configure(api_key=config.GEMINI_API_KEY)

def analyze_risk(text, keywords):
    """Gemini에게 위험도 분석 요청"""
    if not config.GEMINI_API_KEY:
        return "API Key 없음", "MEDIUM"
    
    prompt = f"""
    [역할] 너는 사인버 보안 위협 인텔리전스 분석가야.
    [상황] 아래 텍스트에서 키워드({', '.join(keywords)})가 발견됨.
    [요청] 다음 정보를 분석해서 정해진 형식으로 답변해줘.

    1. 공격 주체(Attacker Group): 해킹 그룹이나 공격자 이름이 있다면 추출(없으면 '식별 불가'라고 적을 것)
    2. 위험도(Risk): HIGH / MEDIUM / LOW
    3. 요약(Summary): 위협 내용 한글 3줄 요약

    [텍스트]
    {text[:2000]}

    [답변형식-> 반드시 준수]
    Attacker: [공격그룹명]
    Risk: [등급]
    Summary: [요약 내용]
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        content = response.text
        
        risk = "LOW"
        if "HIGH" in content: risk = "HIGH"
        elif "MEDIUM" in content: risk = "MEDIUM"
        
        return content, risk
    except Exception as e:
        print(f"[!] AI 분석 오류: {e}")
        return "분석 실패", "LOW"
