"""
요청/응답에 사용하는 Pydantic 모델 정의
- FastAPI 가 자동으로 유효성 검증 및 스키마(OpenAPI) 생성을 해줍니다.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class EchoIn(BaseModel):
    """ /echo 엔드포인트의 입력 모델 """
    text: str  # 에코할 문자열


class EchoOut(BaseModel):
    """ /echo 엔드포인트의 출력 모델 """
    text: str   # 입력 그대로 반환
    length: int # 입력 문자열 길이


class UploadOut(BaseModel):
    """
    /upload 업로드 성공 시의 응답 모델
    - 저장된 파일명(중복 방지를 위해 원본에서 변형될 수 있음)
    - EXIF 에서 추출한 촬영일 (YYYY-MM-DD) - 없으면 None
    """
    filename: str
    taken_date: Optional[str] = Field(None, description="YYYY-MM-DD")


class FileItem(BaseModel):
    """
    파일 목록(/files)에서 사용하는 항목 모델
    - size_bytes: 파일 크기(바이트)
    - uploaded_at: 파일 저장(수정) 시각 ISO 문자열
    - taken_date: EXIF 촬영일(없으면 None)
    """
    filename: str
    size_bytes: int
    uploaded_at: str
    taken_date: Optional[str] = None


class CalendarMonthSummary(BaseModel):
    """
    특정 연/월에 대해 사진이 있는 날짜 요약
    - days: 사진이 존재하는 '일(day)' 목록
    - count_by_day: 날짜(문자열) → 해당 날짜의 사진 개수
    """
    year: int
    month: int
    days: List[int]
    count_by_day: dict
