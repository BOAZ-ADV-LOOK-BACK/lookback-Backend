# 캘린더 관련 API 모음
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.api.v1.endpoints import login, users, google, calendar, data_preprocessing


import httpx
import json

router = APIRouter()



### 캘린더 API
# 1. 캘린더 데이터 요청
# 2. 전처리
# 3. dynamodb에 비동기로 삽입
# 4. 프론트로 데이터 return
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