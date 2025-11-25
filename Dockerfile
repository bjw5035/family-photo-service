# --- 빌드 스테이지 ---
# slim 이미지를 사용해 용량을 줄입니다.
FROM python:3.11-slim AS build
WORKDIR /app

# 종속성 먼저 설치 (레이어 캐시 효율)
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# --- 런타임 스테이지 ---
FROM python:3.11-slim
# 파이썬 출력 버퍼링 비활성화 (로그 실시간 표시)
ENV PYTHONUNBUFFERED=1 
WORKDIR /app

# 빌드 스테이지에서 설치한 패키지를 복사
COPY --from=build /install /usr/local

# 애플리케이션 코드 복사
COPY app ./app

# 업로드 파일 저장용 디렉터리 생성
RUN mkdir -p /app/data

# 컨테이너 포트 노출
EXPOSE 8000

# 기본 API_KEY (운영에서는 런타임 -e 로 주입)
ENV API_KEY=dev-key

# uvicorn 으로 앱 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
