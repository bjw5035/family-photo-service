# 개발 편의를 위한 단축 명령 모음

# 로컬 개발 서버 실행 (자동 리로드)
run:
\tuvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 도커 이미지 빌드
docker-build:
\tdocker build -t family-photo:dev .

# 도커 실행 (호스트 data 디렉터리를 컨테이너에 마운트)
docker-run:
\tdocker run --rm -p 8000:8000 -e API_KEY=dev-key -v $$PWD/data:/app/data family-photo:dev
