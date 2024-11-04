from fastapi.responses import RedirectResponse
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from google_auth_oauthlib.flow import Flow
from starlette.requests import Request
import requests
import logging

import json
logging.basicConfig(level=logging.INFO)

router = APIRouter()


CLIENT_SECRETS_FILE = 'client_secret_639048076528-0mqbo91cf5t0fq5604u0tblqnaka8thp.apps.googleusercontent.com.json'

SCOPES = 'https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/calendar.readonly'

# SCOPES_STR = ' '.join(SCOPES)

REDIRECT_URI='https://look-back.site/auth/callback'


# 요청 본문에 필요한 데이터 스키마 정의
class TokenData(BaseModel):
    access_token: str

    
       
def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }


@router.get("/login")
async def login():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES_STR,
        redirect_uri=REDIRECT_URI
    )
    authorization_url, state = flow.authorization_url(access_type='offline')
    return RedirectResponse(url=authorization_url)

@router.get("/callback")
async def exchange_code_token(request: Request):
    
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES_STR,
        redirect_uri=REDIRECT_URI,
    )
    
    authorization_response = str(request.url)
    flow.fetch_token(authorization_response=authorization_response )
    
    if not flow.credentials:
        raise HTTPException(status_code=400, detail="Failed to fetch token")
    
    credentials = flow.credentials
    
    response = RedirectResponse(url='/preprocess/calendar')
    
    #user info - 프로필, 이메일도 처리하는 함수나 API 하나 만들어서 추가
    response.set_cookie(key='credentials', value=json.dumps(credentials_to_dict(credentials)), httponly=True)
    
    return response





@router.post("/save-token")
async def save_token(token_data: TokenData):
    # 액세스 토큰 출력 (DB 저장이나 추가 작업을 여기에 작성)
    print(f"Received Access Token: {token_data.access_token}", flush=True)
    logging.info(f"Received Access Token: {token_data.access_token}")
    
    credentials = token_data

    response = RedirectResponse(url='/preprocess/calendar')
    response.set_cookie(key='credentials', value=json.dumps(credentials_to_dict(credentials)), httponly=True)
    
    try:
        # Google 사용자 정보 API 
        
        user_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
        headers = {"Authorization": f"Bearer {token_data.access_token}"}
        
        response = requests.get(user_info_url, headers=headers)

        # API 호출 실패 시 오류 반환
        if response.status_code != 200:
            logging.error("Failed to fetch user info from Google")
            raise HTTPException(status_code=400, detail="Failed to fetch user info from Google")

        # 사용자 정보 파싱
        user_data = response.json()
        logging.info(f"User data received: {user_data}")

        # 사용자 정보를 반환합니다.
        return {
            "email": user_data.get("email"),
            "name": user_data.get("name")
        }

    except Exception as e:
        logging.error(f"Error fetching user info: {str(e)}")
        raise HTTPException(status_code=500, detail="Intern server error while fetching user info")



    return {"message": "Token received and processed"}
