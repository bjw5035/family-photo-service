"""
FastAPI 애플리케이션 엔트리포인트

주요 엔드포인트
- GET  /healthz         : 단순 헬스 체크 (무인증)
- POST /echo            : 에코 API (간단 인증: X-API-Key)
- POST /upload          : 이미지 업로드 (간단 인증)
- GET  /files           : 업로드된 파일 메타 목록 (간단 인증)
- GET  /download/{fn}   : 파일 다운로드 (간단 인증)
- GET  /calendar/y/m    : 월별 사진 요약 (간단 인증)
- GET  /metrics         : Prometheus 수집용 메트릭 (무인증)

관측(Observability)
- prometheus_client 의 Counter/Histogram 으로 엔드포인트별 요청 수/지연 시간 기록
- utils.setup_logging() 으로 JSON 구조화 로그 출력
"""

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from functools import wraps  # 데코레이터 적용 시 원본 함수 메타 유지
import logging

from .auth import verify_api_key
from .models import EchoIn, EchoOut, UploadOut
from . import storage, calendar
from .utils import setup_logging

# 애플리케이션 시작 시 로깅을 JSON 포맷으로 세팅
setup_logging()
log = logging.getLogger("app")

# Prometheus 메트릭: 엔드포인트 라벨을 포함하도록 설계
REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["endpoint"],
)
LATENCY = Histogram(
    "http_request_latency_seconds",
    "Request latency",
    ["endpoint"],
)

# FastAPI 인스턴스 생성 (문서화: /docs, /openapi.json)
app = FastAPI(title="Family Photo Service (MVP)")


def metric(endpoint: str):
    """
    엔드포인트별로 요청 수와 지연 시간(histogram)을 자동 수집하는 데코레이터.
    - 내부에서 REQUESTS/LATENCY 메트릭에 라벨(endpoint)을 부여합니다.
    """
    def wrapper(func):
        @wraps(func)
        async def inner(*args, **kwargs):
            REQUESTS.labels(endpoint=endpoint).inc()
            # with 구문으로 histogram 타이머를 시작/종료
            with LATENCY.labels(endpoint=endpoint).time():
                return await func(*args, **kwargs)

        return inner
    return wrapper


@app.get("/healthz", response_class=PlainTextResponse)
@metric("healthz")
async def healthz():
    """컨테이너/로드밸런서 헬스체크 용도. 인증 불필요."""
    return "ok"


@app.post("/echo", response_model=EchoOut, dependencies=[Depends(verify_api_key)])
@metric("echo")
async def echo(body: EchoIn):
    """
    입력으로 받은 텍스트를 그대로 반환하면서 길이 정보도 함께 내려줍니다.
    - 간단한 인증 필요 (X-API-Key)
    """
    result = EchoOut(text=body.text, length=len(body.text))
    # 구조화 로그로 길이 정보 같이 기록 (extra 필드는 JsonFormatter 에서 자동 포함 X -> message에 포함 권장)
    log.info(f"echo called, length={result.length}")
    return result


@app.post("/upload", response_model=UploadOut, dependencies=[Depends(verify_api_key)])
@metric("upload")
async def upload(file: UploadFile = File(...)):
    """
    멀티파트로 올라온 파일을 data/ 디렉토리에 저장합니다.
    - 동일 파일명 충돌을 방지하기 위해 storage.save_file 이 이름을 조정할 수 있습니다.
    - 저장 완료 후 EXIF 촬영일을 추출해 함께 반환합니다.
    """
    # 파일 전체 바이트를 한 번에 읽습니다. (대용량이면 스트리밍 업로드 고려)
    content = await file.read()
    saved_name = storage.save_file(file.filename, content)

    # 촬영일(EXIF) 추출 (없을 수 있음)
    taken = storage._exif_taken_date(storage.get_path(saved_name))

    log.info(f"uploaded filename={saved_name}, taken_date={taken}")
    return UploadOut(filename=saved_name, taken_date=taken)


@app.get("/files", dependencies=[Depends(verify_api_key)])
@metric("files")
async def files():
    """
    저장된 파일 목록과 메타 정보를 반환합니다.
    - 최신 업로드순 정렬
    """
    return [f.dict() for f in storage.list_files()]


@app.get("/download/{filename}", dependencies=[Depends(verify_api_key)])
@metric("download")
async def download(filename: str):
    """
    주어진 파일명을 다운로드합니다.
    - 파일이 존재하지 않으면 404
    """
    path = storage.get_path(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path)


@app.get("/calendar/{year}/{month}", dependencies=[Depends(verify_api_key)])
@metric("calendar")
async def calendar_month(year: int, month: int):
    """
    특정 년/월의 사진 분포를 요약하여 반환합니다.
    - EXIF 촬영일이 있으면 우선 사용
    - 없으면 업로드 시각으로 대체
    """
    files = storage.list_files()
    return calendar.month_summary(files, year, month).dict()


@app.get("/metrics")
async def metrics():
    """
    Prometheus 스크레이핑 엔드포인트
    - 인증 없이 공개하는 것이 일반적 (보안 요구사항에 따라 보호 필요)
    """
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
