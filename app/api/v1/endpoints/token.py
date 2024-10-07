from fastapi.responses import RedirectResponse
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
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

    return {"message": "Token received and processed"}