import streamlit as st
import sqlite3
import openai
import os
from dotenv import load_dotenv
from contextlib import contextmanager
from difflib import SequenceMatcher

# 베타 테스트 설정
BETA_TEST = True  # 베타 테스트가 끝나면 False로 변경

# Streamlit configuration
st.set_page_config(
    page_title="의료 상담 챗봇",
    page_icon="🏥",
    layout="wide"
)

# Server configuration
if __name__ == "__main__":
    import sys
    sys.argv = ["streamlit", "run", __file__, "--server.address", "0.0.0.0", "--server.port", "8504"]

# Load environment variables
load_dotenv()

# Get API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    st.error("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")
    st.stop()

# Database context manager
@contextmanager
def get_db_connection():
    conn = sqlite3.connect("qa.db")
    try:
        yield conn
    finally:
        conn.close()

# ▶️ SQLite 초기화
def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS qa_dataset (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                source TEXT NOT NULL,
                approved BOOLEAN DEFAULT FALSE,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

# ▶️ 유사도 계산 함수
def similar(a, b):
    # 문장을 단어 단위로 분리하여 비교
    a_words = set(a.split())
    b_words = set(b.split())
    
    # 공통 단어 수 계산
    common_words = a_words.intersection(b_words)
    
    # 전체 단어 수
    total_words = len(a_words.union(b_words))
    
    # 유사도 계산 (0.0 ~ 1.0)
    if total_words == 0:
        return 0.0
    return len(common_words) / total_words

# ▶️ 유사한 질문 찾기
def find_similar_question(question, threshold=0.8):  # 임계값을 0.8로 높임
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT question, answer FROM qa_dataset")
        saved_qa = c.fetchall()
        
        for saved_q, saved_a in saved_qa:
            if similar(question, saved_q) > threshold:
                return saved_q, saved_a
    return None, None

# ▶️ GPT 응답 생성 함수
def gpt_answer(question):
    try:
        # 먼저 유사한 질문이 있는지 확인
        similar_q, similar_a = find_similar_question(question)
        if similar_q:
            return similar_a  # 답변만 반환
        
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "당신은 의료 상담 전문가입니다. 정확하고 전문적인 답변을 제공해주세요. 모든 답변은 한글로 작성해주세요."},
                {"role": "user", "content": question}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        st.error(f"GPT 응답 생성 중 오류가 발생했습니다: {str(e)}")
        return None

# ▶️ 응답 저장 함수
def save_answer(question, answer, approved=True):
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO qa_dataset (question, answer, source, approved) 
                VALUES (?, ?, ?, ?)
            """, (question, answer, "GPT-4", approved))
            conn.commit()
            return True
    except Exception as e:
        st.error(f"응답 저장 중 오류가 발생했습니다: {str(e)}")
        return False

# ▶️ 저장된 데이터 보기 함수
def view_saved_data():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT question, answer, created_at FROM qa_dataset ORDER BY created_at DESC")
        saved_data = c.fetchall()
        return saved_data

# ▶️ 앱 시작
init_db()
st.title("의료 상담 챗봇 베타 테스트")


# 탭 생성 (베타 테스트 중일 때만 저장된 상담 보기 탭 표시)
if BETA_TEST:
    tab1, tab2 = st.tabs(["상담하기", "저장된 상담 보기"])
else:
    tab1 = st.container()

with tab1:
    # Session state 초기화
    if 'last_question' not in st.session_state:
        st.session_state.last_question = ''

    # 사용자 입력이 변경될 때 호출되는 함수
    def on_input_change():
        current_question = st.session_state.question
        if current_question and current_question != st.session_state.last_question:
            st.session_state.last_question = current_question
            with st.spinner("응답을 생성하는 중..."):
                answer = gpt_answer(current_question)
                if answer:
                    st.session_state.current_answer = answer

    # 사용자 입력
    question = st.text_input("질문을 입력하고 Enter 키를 누르세요:", key="question", on_change=on_input_change)

    # 응답 표시
    if 'current_answer' in st.session_state:
        st.markdown("#### GPT 응답")
        st.write(st.session_state.current_answer)
        
        # 저장 옵션
        if st.button("이 응답 저장하기"):
            if save_answer(question, st.session_state.current_answer):
                st.success("응답이 qa.db에 저장되었습니다.")

if BETA_TEST:
    with tab2:
        st.markdown("### 저장된 상담 내역")
        saved_data = view_saved_data()
        if saved_data:
            for q, a, date in saved_data:
                with st.expander(f"질문: {q} ({date})"):
                    st.write(f"답변: {a}")
        else:
            st.info("아직 저장된 상담 내역이 없습니다.")
