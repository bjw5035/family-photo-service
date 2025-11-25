"""
공용 유틸리티
- JSON 형식의 구조화 로그 포맷터
- 루트 로거 설정 함수
"""

import logging
import sys
import json
import time


class JsonFormatter(logging.Formatter):
    """
    표준 logging.Formatter 를 상속하여 로그를 JSON 문자열로 변환합니다.
    - 타임스탬프, 레벨, 로거명, 메시지, 예외정보 등을 필드로 담습니다.
    - 운영 환경에서 수집/분석(예: Loki, Elastic, CloudWatch Logs)에 유리합니다.
    """

    def format(self, record: logging.LogRecord) -> str:
        base = {
            # ISO 형식 비슷하게 기록. (timezone 오프셋 포함)
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,       # INFO, ERROR 등 로그 레벨
            "logger": record.name,           # 로거명 (예: 'app')
            "message": record.getMessage(),  # 최종 메시지 문자열
        }

        # 예외가 포함된 로그의 경우 스택트레이스도 JSON 에 넣습니다.
        if record.exc_info:
            base["exc_info"] = self.formatException(record.exc_info)

        # ensure_ascii=False 로 한글이 \uXXXX 로 깨지지 않게 합니다.
        return json.dumps(base, ensure_ascii=False)


def setup_logging() -> None:
    """
    애플리케이션 시작 시 호출하여 루트 로거를 JSON 포맷으로 세팅합니다.
    - 기본 레벨은 INFO
    - 핸들러는 stdout 으로 출력 (컨테이너/쿠버네티스 환경에서 표준)
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # 기존 핸들러를 덮어쓰는 방식으로 단일 핸들러만 유지
    root.handlers = [handler]
