# 캘린더 관련 API 모음
from fastapi import APIRouter, HTTPException, Depends, logger
from pydantic import BaseModel
from app.api.v1.endpoints import login, users, google, calendar 
from app.api.deps import get_current_user
from app.models.user import User
import httpx
import json

from app.db.dynamo import put_calendar_list

router = APIRouter()

async def refresh_google_token(refresh_token: str):
    """Google refresh token을 사용해 새로운 access token을 발급받습니다."""
    
    # client secrets 파일에서 설정 읽기
    with open("client_secret_639048076528-0mqbo91cf5t0fq5604u0tblqnaka8thp.apps.googleusercontent.com.json", "r") as f:
        client_config = json.load(f)["web"]

    # Google OAuth 토큰 갱신 엔드포인트
    token_url = "https://oauth2.googleapis.com/token"
    
    # 요청 데이터 준비
    token_data = {
        "client_id": client_config["client_id"],
        "client_secret": client_config["client_secret"],
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=token_data)
            response.raise_for_status()  # 에러 체크
            
            token_info = response.json()
            
            if "access_token" not in token_info:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to refresh access token"
                )
                
            return token_info["access_token"]
            
    except httpx.HTTPError as e:
        logger.error(f"Error refreshing Google token: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to refresh Google access token"
        )
    except Exception as e:
        logger.error(f"Unexpected error while refreshing token: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during token refresh"
        )


### 캘린더 API
# 1. 캘린더 데이터 요청
# 2. 전처리
# 3. dynamodb에 비동기로 삽입
# 4. 프론트로 데이터 return

@router.post("/sync-calendar")
async def sync_calendar(current_user: User = Depends(get_current_user)):
    try:
        # refresh token으로 새 access token 획득
        new_access_token = await refresh_google_token(current_user.refresh_token)
        
        # 캘린더 동기화
        await put_calendar_list(new_access_token)
        
        return {
            "success": True,
            "message": "Calendar synchronized successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/dashboard-data")
async def get_dashboard_data(code):
    # token_info 예시는 print 후 확인 요망
    token_info = await google.get_access_token(code)


    # 1. 캘린더 데이터 요청
    calendar_data_origin = await google.get_calendar_data(code)

    # 2. 전처리
    # data_preprocessing.py 내부 함수 참고

    # 3. dynamodb 비동기 삽입
    # data_preprocessing.py 내부 함수 참고
    
    # 4. 프론트로 리턴
    # 2번에서 전처리 한 결과 리턴해주면 됨
    # 향후 프론트에서 이 데이터 받아서 알아서 잘 각 시각화 component에 잘 매핑