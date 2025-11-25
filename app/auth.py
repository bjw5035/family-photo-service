"""
간단한 API 키 인증 모듈

- 요청 헤더의 `X-API-Key` 값이 .env(또는 환경변수)로 주입된 API_KEY 와 일치하는지 검증합니다.
- FastAPI의 Depends 로 엔드포인트에 쉽게 적용할 수 있습니다.
"""

from fastapi import Header, HTTPException, status
import os

# 환경변수에서 API 키를 읽습니다. (.env 를 로딩했다면 dotenv 가 환경변수에 반영)
# 개발 편의를 위해 기본값 'dev-key' 를 둡니다. (운영에서는 반드시 바꾸세요)
API_KEY = os.getenv("API_KEY", "dev-key")


def verify_api_key(x_api_key: str = Header(None)):
    """
    요청 헤더에서 X-API-Key 를 받아 검증합니다.
    - 값이 없거나, 설정한 키와 다르면 401 Unauthorized 를 반환합니다.

    Parameters
    ----------
    x_api_key : str
        요청 헤더 'X-API-Key' 값. (FastAPI가 자동 주입)

    Raises
    ------
    HTTPException(401)
        인증 실패 시 예외를 발생시켜 FastAPI 가 401 응답을 반환합니다.
    """
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
