# 구글 콘솔과 상호작용 관련
from fastapi import APIRouter, HTTPException, Depends, Request
import httpx
import json
router = APIRouter()



### Access Token 받아오는 함수,
# parameter - authorization code
# return - json type의 token_info 를 반환함
async def get_access_token(code):
        token_url = "https://oauth2.googleapis.com/token"
        token_info = ""
        # 나중에 Google
        with open("client_secret_639048076528-0mqbo91cf5t0fq5604u0tblqnaka8thp.apps.googleusercontent.com.json", "r") as f:
            client_config = json.load(f)["web"]

        token_data = {
            "code": code,
            "client_id": client_config["client_id"],
            "client_secret": client_config["client_secret"],
            "redirect_uri": "postmessage",
            "grant_type": "authorization_code"
        }

        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_url, data=token_data)
            token_response.raise_for_status()
            token_info = token_response.json()
        
        return token_info


### 캘린더 데이터 통째로 받아오는 함수
# parameter - authorization code
# return - json type의 calendar data
async def get_calendar_data(code):
    
    # access token 받아오기
    token_info = get_access_token(code)

    # calendar data 요청

