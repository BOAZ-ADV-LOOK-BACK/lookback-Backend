from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import requests

router = APIRouter()

# Google access token을 받기 위한 Pydantic 스키마
class TokenData(BaseModel):
    access_token: str

# Google 사용자 정보를 저장할 모델
class GoogleUser(BaseModel):
    name: str
    email: str
    picture: str

# 액세스 토큰을 받아서 Google 사용자 정보 API에서 정보를 가져오는 엔드포인트
@router.post("/google-login")
async def google_login(token_data: TokenData):
    access_token = token_data.access_token
    user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Google 사용자 정보 가져오기
    response = requests.get(user_info_url, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch user info from Google")
    
    user_data = response.json()
    google_user = GoogleUser(
        name=user_data.get("name"),
        email=user_data.get("email"),
        picture=user_data.get("picture"),
    )

    # 추가로 이 정보를 DB에 저장하거나 다른 처리를 할 수 있습니다.
    # 예시: DB에 사용자 정보 저장하는 로직 추가 가능

    return {"message": "User logged in successfully", "user": google_user}
