from fastapi.responses import RedirectResponse
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import requests
import logging

import json
logging.basicConfig(level=logging.INFO)

router = APIRouter()


REDIRECT_URI = 'https://api.look-back.site/api/v1/save-token'

# 요청 본문에 필요한 데이터 스키마 정의
class TokenData(BaseModel):
    access_token: str


def credentials_to_dict(credentials):
    return {
        'token': credentials.access_token,
#        'refresh_token': credentials.refresh_token,
        #'token_uri': credentials.token_uri,
        #'client_id': credentials.client_id,
        #'client_secret': credentials.client_secret,
        #'scopes': credentials.scopes
    }

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