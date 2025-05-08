# 의료 상담 챗봇

GPT-4를 활용한 의료 상담 챗봇 애플리케이션입니다.

## 기능

- GPT-4 기반 의료 상담 서비스
- 질문-답변 데이터베이스 저장
- 유사 질문 검색 기능
- 베타 테스트 모드 지원

## 설치 방법

1. 저장소 클론
```bash
git clone [repository-url]
cd [repository-name]
```

2. 필요한 패키지 설치
```bash
pip install -r requirements.txt
```

3. 환경 변수 설정
`.env` 파일을 생성하고 다음 내용을 추가하세요:
```
OPENAI_API_KEY=your_api_key_here
```

## 실행 방법

```bash
streamlit run app.py
```

## 주의사항

- 이 애플리케이션은 의료 상담을 위한 참고용 도구입니다.
- 실제 의료 진단이나 처방을 대체할 수 없습니다.
- 심각한 증상이 있는 경우 반드시 전문 의료기관을 방문하세요.

## 라이선스

MIT License 