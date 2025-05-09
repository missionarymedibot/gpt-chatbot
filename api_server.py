from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os
import sqlite3
from contextlib import contextmanager
from difflib import SequenceMatcher
import sys

# Load environment variables

# OpenAI API 설정
OpenAI.api_key = os.getenv("OPENAI_API_KEY")
if not OpenAI.api_key:
    print("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.", file=sys.stderr)
    raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 운영시에는 특정 도메인만 허용하도록 수정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database context manager
@contextmanager
def get_db_connection():
    conn = sqlite3.connect("qa.db")
    try:
        yield conn
    finally:
        conn.close()

# 유사도 계산 함수
def similar(a, b):
    a_words = set(a.split())
    b_words = set(b.split())
    common_words = a_words.intersection(b_words)
    total_words = len(a_words.union(b_words))
    if total_words == 0:
        return 0.0
    return len(common_words) / total_words

# 유사한 질문 찾기
def find_similar_question(question, threshold=0.8):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT question, answer FROM qa_dataset")
        saved_qa = c.fetchall()
        
        for saved_q, saved_a in saved_qa:
            if similar(question, saved_q) > threshold:
                return saved_q, saved_a
    return None, None

# GPT 응답 생성 함수
def gpt_answer(question):
    try:
        # 유사한 질문 확인
        similar_q, similar_a = find_similar_question(question)
        if similar_q:
            return similar_a
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "당신은 의료 상담 전문가입니다. 정확하고 전문적인 답변을 제공해주세요."},
                {"role": "user", "content": question}
            ],
            temperature=0.5,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        print("❗ GPT 호출 오류:", e)
        raise HTTPException(status_code=500, detail=str(e))

# 응답 저장 함수
def save_answer(question, answer, approved=True):
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO qa_dataset (question, answer, source, approved) 
                VALUES (?, ?, ?, ?)
            """, (question, answer, "GPT-3.5", approved))
            conn.commit()
            return True
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 요청 모델
class ChatRequest(BaseModel):
    userRequest: dict
    bot: dict
    action: dict

# 응답 모델
class ChatResponse(BaseModel):
    version: str = "2.0"
    template: dict

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        # 사용자 메시지 추출
        user_message = request.userRequest.get("utterance", "")
        
        # GPT 응답 생성
        answer = gpt_answer(user_message)
        
        # 응답 저장
        save_answer(user_message, answer)
        
        # 카카오톡 응답 형식
        response = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": answer
                        }
                    }
                ]
            }
        }
        
        return response
    except Exception as e:
        print("❗[ERROR in /api/chat]:", e)
        raise HTTPException(status_code=500, detail=str(e))

# 서버 상태 확인
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 