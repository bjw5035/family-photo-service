"""
파일 저장/조회 관련 로직
- data/ 디렉토리에 파일을 저장하고, 목록을 조회하며, EXIF 메타에서 촬영일을 추출합니다.
"""

from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .models import FileItem

# 이미지 메타데이터(EXIF) 파싱을 위해 Pillow 사용
from PIL import Image
from PIL.ExifTags import TAGS


# 업로드 파일이 저장될 루트 디렉토리. (상대경로: 프로젝트 루트 기준)
DATA_DIR = Path("data")
# 존재하지 않으면 생성 (parents=True: 상위 경로까지 생성)
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _exif_taken_date(p: Path) -> Optional[str]:
    """
    주어진 이미지 파일 Path 에서 EXIF 의 촬영일(DateTimeOriginal)을 추출합니다.
    - EXIF 없거나 파싱 실패 시 None 반환
    - 반환 형식은 'YYYY-MM-DD'

    주의: 일부 이미지 포맷/편집도구는 EXIF 가 없을 수 있습니다.
    """
    try:
        with Image.open(p) as img:
            exif = img.getexif()
            if not exif:
                return None

            # EXIF 키(숫자)를 사람이 읽는 태그명으로 매핑
            tag_map = {TAGS.get(k): v for k, v in exif.items()}

            # 일반적으로 촬영일은 DateTimeOriginal 에 들어있습니다.
            dt = tag_map.get("DateTimeOriginal") or tag_map.get("DateTime")
            if not dt:
                return None

            # EXIF 날짜 형식: 'YYYY:MM:DD HH:MM:SS'
            # 날짜 부분만 잘라서 'YYYY-MM-DD' 로 변환
            return dt.split(" ")[0].replace(":", "-")
    except Exception:
        # 이미지가 아니거나, 손상된 파일 등 예외 상황에서는 None 처리
        return None


def save_file(filename: str, content: bytes) -> str:
    """
    파일을 data/ 에 저장합니다.
    - 동일 파일명이 이미 존재하면 '이름_1.ext', '이름_2.ext' ... 식으로 충돌을 피합니다.
    - 실제 저장된(충돌 조정 후) 파일명을 반환합니다.
    """
    path = DATA_DIR / filename

    if path.exists():
        # 파일명 충돌 시 뒤에 숫자 suffix 를 붙여 새로운 이름을 만듭니다.
        stem = path.stem   # 확장자 제외한 이름
        suffix = path.suffix  # '.jpg' 같은 확장자
        i = 1
        while True:
            new = DATA_DIR / f"{stem}_{i}{suffix}"
            if not new.exists():
                path = new
                break
            i += 1

    # 실제 바이트를 기록
    path.write_bytes(content)
    return path.name


def list_files() -> List[FileItem]:
    """
    data/ 아래의 파일들을 조회하여 메타 정보 목록을 만듭니다.
    - 업로드(수정)시각은 파일의 mtime 을 사용합니다.
    - EXIF 촬영일은 가능한 경우에만 추출합니다.
    - 최신순(업로드 시각 내림차순)으로 정렬하여 반환합니다.
    """
    items: List[FileItem] = []

    for p in DATA_DIR.iterdir():
        if p.is_file():
            stat = p.stat()
            uploaded_at = datetime.fromtimestamp(stat.st_mtime).isoformat()

            items.append(
                FileItem(
                    filename=p.name,
                    size_bytes=stat.st_size,
                    uploaded_at=uploaded_at,
                    taken_date=_exif_taken_date(p),
                )
            )

    # 최신 업로드가 먼저 오도록 정렬
    return sorted(items, key=lambda x: x.uploaded_at, reverse=True)


def get_path(filename: str) -> Path:
    """
    주어진 파일명을 data/ 기준의 실제 파일 경로로 변환합니다.
    - FastAPI 의 FileResponse 에 전달할 때 사용합니다.
    """
    return DATA_DIR / filename
