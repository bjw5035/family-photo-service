"""
캘린더(월별 요약) 관련 로직
- 파일 목록을 입력받아 특정 연/월에 해당하는 날짜별 개수를 계산합니다.
"""

from typing import Dict, Iterable
from .models import CalendarMonthSummary, FileItem
from datetime import datetime
from collections import Counter


def month_summary(files: Iterable[FileItem], year: int, month: int) -> CalendarMonthSummary:
    """
    월별 사진 요약을 계산합니다.

    규칙
    - 우선순위 1: EXIF 촬영일(taken_date)
    - 우선순위 2: 업로드 시각(uploaded_at, ISO 문자열)

    Parameters
    ----------
    files : Iterable[FileItem]
        /files 에서 반환되는 파일 메타 목록
    year : int
        대상 연도
    month : int
        대상 월(1~12)

    Returns
    -------
    CalendarMonthSummary
        days: 사진이 존재하는 '일(day)' 목록 (중복 제거)
        count_by_day: '일(day)'별 사진 개수
    """
    days = []
    cnt: Dict[int, int] = Counter()

    for f in files:
        # taken_date 가 있으면 YYYY-MM-DD 로 파싱, 없으면 uploaded_at(ISO) 사용
        if f.taken_date:
            dt = datetime.strptime(f.taken_date, "%Y-%m-%d")
        else:
            dt = datetime.fromisoformat(f.uploaded_at)

        # 요청한 연/월만 집계
        if dt.year == year and dt.month == month:
            d = dt.day
            days.append(d)
            cnt[d] += 1

    return CalendarMonthSummary(
        year=year,
        month=month,
        days=sorted(set(days)),                              # 중복 제거 후 정렬
        count_by_day={str(k): v for k, v in sorted(cnt.items())},  # 키를 문자열로
    )
