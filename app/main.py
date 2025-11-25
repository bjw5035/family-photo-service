"""
FastAPI 애플리케이션 엔트리포인트 (UI + API)

UI (HTML)
- GET  /               : 홈 화면
- GET  /upload-page    : 업로드 화면
- POST /upload-ui      : 업로드 폼 처리 후 갤러리로 리다이렉트
- GET  /gallery        : 갤러리 화면
- GET  /calendar-page  : 이번 달 캘린더 요약 화면
- GET  /images/{fn}    : 브라우저에서 직접 보는 이미지

API (JSON)
- GET  /healthz        : 헬스 체크
- POST /echo           : 에코 API (API 키 필요)
- POST /upload         : 파일 업로드 API (API 키 필요)
- GET  /files          : 파일 메타 목록 (API 키 필요)
- GET  /download/{fn}  : 파일 다운로드 (API 키 필요)
- GET  /calendar/y/m   : 월별 사진 요약 (API 키 필요)
- GET  /metrics        : Prometheus 메트릭
"""

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Depends,
    HTTPException,
    Request,
    Form,
)
from fastapi.responses import (
    FileResponse,
    PlainTextResponse,
    HTMLResponse,
    RedirectResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from functools import wraps
from datetime import datetime
import logging

from .auth import verify_api_key
from .models import EchoIn, EchoOut, UploadOut
from . import storage, calendar
from .utils import setup_logging

# 로깅 JSON 포맷 세팅
setup_logging()
log = logging.getLogger("app")

# Prometheus 메트릭
REQUESTS = Counter("http_requests_total", "Total HTTP requests", ["endpoint"])
LATENCY = Histogram("http_request_latency_seconds", "Request latency", ["endpoint"])

# FastAPI 인스턴스
app = FastAPI(title="Family Photo Service (MVP)")

# 템플릿 및 정적 파일 설정
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


def metric(endpoint: str):
    """
    엔드포인트별 요청 수 / 지연시간 수집용 데코레이터
    """

    def wrapper(func):
        @wraps(func)
        async def inner(*args, **kwargs):
            REQUESTS.labels(endpoint=endpoint).inc()
            with LATENCY.labels(endpoint=endpoint).time():
                return await func(*args, **kwargs)

        return inner

    return wrapper


# ------------------------
# UI(HTML) 엔드포인트
# ------------------------


@app.get("/", response_class=HTMLResponse, name="index_page")
@metric("index_page")
async def index_page(request: Request):
    """
    홈 화면 (간단 소개 + 메뉴)
    """
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "홈",
        },
    )


@app.get("/upload-page", response_class=HTMLResponse, name="upload_page")
@metric("upload_page")
async def upload_page(request: Request, message: str | None = None):
    """
    업로드 폼 화면
    """
    return templates.TemplateResponse(
        "upload.html",
        {
            "request": request,
            "title": "업로드",
            "message": message,
        },
    )


@app.post("/upload-ui", name="upload_ui")
@metric("upload_ui")
async def upload_ui(request: Request, file: UploadFile = File(...)):
    """
    업로드 폼에서 올라온 파일 처리 (UI 전용)
    - API 키 없이 사용
    - 저장 후 갤러리로 리다이렉트
    """
    content = await file.read()
    saved_name = storage.save_file(file.filename, content)
    taken = storage._exif_taken_date(storage.get_path(saved_name))

    log.info(f"[UI] uploaded filename={saved_name}, taken_date={taken}")

    # 업로드 후 갤러리 화면으로 이동
    return RedirectResponse(url="/gallery", status_code=303)


@app.get("/gallery", response_class=HTMLResponse, name="gallery_page")
@metric("gallery_page")
async def gallery_page(request: Request):
    """
    갤러리 화면
    - data/ 디렉토리의 파일 목록을 읽어서 썸네일(실제 이미지)로 표시
    """
    files = storage.list_files()
    return templates.TemplateResponse(
        "gallery.html",
        {
            "request": request,
            "title": "갤러리",
            "files": files,
        },
    )


@app.get("/calendar-page", response_class=HTMLResponse, name="calendar_page")
@metric("calendar_page")
async def calendar_page(request: Request):
    """
    이번 달 캘린더 요약 화면
    - 현재 날짜 기준 연/월로 month_summary 호출
    """
    now = datetime.now()
    files = storage.list_files()
    summary = calendar.month_summary(files, now.year, now.month)

    return templates.TemplateResponse(
        "calendar.html",
        {
            "request": request,
            "title": "캘린더",
            "summary": summary,
        },
    )


@app.get("/images/{filename}", name="image_raw")
@metric("image_raw")
async def image_raw(filename: str):
    """
    브라우저에서 직접 이미지를 표시하기 위한 엔드포인트
    - attachment 헤더를 넣지 않고 FileResponse 로 그대로 반환
    """
    path = storage.get_path(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    # FileResponse 가 Content-Type 을 적절히 추론 (jpg, png 등)
    return FileResponse(path)


# ------------------------
# API(JSON) 엔드포인트
# ------------------------


@app.get("/healthz", response_class=PlainTextResponse)
@metric("healthz")
async def healthz():
    """헬스 체크 (무인증)"""
    return "ok"


@app.post("/echo", response_model=EchoOut, dependencies=[Depends(verify_api_key)])
@metric("echo")
async def echo(body: EchoIn):
    """에코 API (API 키 필요)"""
    result = EchoOut(text=body.text, length=len(body.text))
    log.info(f"echo called, length={result.length}")
    return result


@app.post("/upload", response_model=UploadOut, dependencies=[Depends(verify_api_key)])
@metric("upload")
async def upload(file: UploadFile = File(...)):
    """
    파일 업로드 API (머신/스크립트용)
    - /upload-ui 는 UI용, /upload 는 API용
    """
    content = await file.read()
    saved_name = storage.save_file(file.filename, content)
    taken = storage._exif_taken_date(storage.get_path(saved_name))

    log.info(f"[API] uploaded filename={saved_name}, taken_date={taken}")
    return UploadOut(filename=saved_name, taken_date=taken)


@app.get("/files", dependencies=[Depends(verify_api_key)])
@metric("files")
async def files():
    """파일 메타 정보 목록 (JSON)"""
    return [f.dict() for f in storage.list_files()]


@app.get("/download/{filename}", dependencies=[Depends(verify_api_key)])
@metric("download")
async def download(filename: str):
    """
    파일 다운로드 API
    - 브라우저 다운로드 용도
    """
    path = storage.get_path(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path)


@app.get("/calendar/{year}/{month}", dependencies=[Depends(verify_api_key)])
@metric("calendar_api")
async def calendar_month(year: int, month: int):
    """월별 사진 요약 JSON API"""
    files = storage.list_files()
    return calendar.month_summary(files, year, month).dict()


@app.get("/metrics")
async def metrics():
    """Prometheus 메트릭 엔드포인트"""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
