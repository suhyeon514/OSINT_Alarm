import psycopg2
import json
import config

def get_conn():
    try:
        return psycopg2.connect(
            host=config.DB_HOST,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
    except Exception as e:
        print(f"[!] DB 접속 오류: {e}")
        return None

def is_duplicate(conn, unique_key):
    """중복 데이터 확인"""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM collected_data WHERE unique_key = %s", (unique_key,))
        return cur.fetchone() is not None

def get_keywords(conn):
    """감시 키워드 로드"""
    with conn.cursor() as cur:
        cur.execute("SELECT keyword FROM search_keywords")
        return [row[0] for row in cur.fetchall()]

def save_data(conn, data_pack):
    """최종 데이터 저장"""
    sql = """
        INSERT INTO collected_data 
        (source, raw_data, unique_key, extracted_tags, matched_keywords, llm_summary, risk_level, processed)
        VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (
                data_pack['source'],
                json.dumps(data_pack['raw_data']),
                data_pack['unique_key'],
                json.dumps(data_pack['extracted']),
                data_pack['matched'],
                data_pack['llm_summary'],
                data_pack['risk_level']
            ))
        conn.commit()
        return True
    except Exception as e:
        print(f"[!] DB 저장 실패: {e}")
        conn.rollback()
        return False
