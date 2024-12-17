# 구글 콘솔과 상호작용 관련
# google.py
from fastapi import APIRouter, HTTPException, Depends, Request
import httpx
import json
import logging

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

### Access Token 받아오는 함수
# parameter - authorization code
# return - json type의 token_info 를 반환함
async def get_access_token(code):
    token_url = "https://oauth2.googleapis.com/token"

        # 클라이언트 구성 읽기
    with open("client_secret_639048076528-0mqbo91cf5t0fq5604u0tblqnaka8thp.apps.googleusercontent.com.json", "r") as f:
        client_config = json.load(f)["web"]

    token_data = {
        "code": code,
        "client_id": client_config["client_id"],
        "client_secret": client_config["client_secret"],
        "redirect_uri": "postmessage",  # 등록된 redirect_uri와 일치해야 함
        "grant_type": "authorization_code",
    }

    # 액세스 토큰 요청
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=token_data)  # 데이터는 body로 전송
        # response.raise_for_status()
        # print("responose: ", response)
        # print("Full Response Text: ", response.text)  # 서버에서 반환한 원본 데이터 출력
        return response.json()  # Access Token 포함된 응답 반환

    


### 캘린더 리스트 요청(캘린더 id 리스트를 받아야 함)
# parameter - authorization code
# return - json type의 calendar data
@router.get("/calendar-list")
async def get_calendar_data(token_info):
    # calendar list 요청
    client = httpx.AsyncClient()
    try:
        response = await client.get(
            "https://www.googleapis.com/calendar/v3/users/me/calendarList",
            headers={"Authorization": f"Bearer {token_info['access_token']}"}
        )
        response.raise_for_status()
        calender_list = response.json()
    finally:
        await client.aclose()  # 명시적으로 닫기

    return calender_list



async def get_calendar_events(access_token, calendar_ids):
   logger.info(f"받은 캘린더 ID 목록: {calendar_ids}")  # 캘린더 ID 로깅
   events_all = []
   
   async with httpx.AsyncClient() as client:
       for calendar_id in calendar_ids:
           logger.info(f"처리 중인 캘린더 ID: {calendar_id}")  # 개별 ID 로깅
           url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
           headers = {"Authorization": f"Bearer {access_token}"}
           
           try:
               response = await client.get(url, headers=headers)
               if response.status_code == 200:
                   events = response.json()
                   events_all.append({
                       'calendar_id': calendar_id,
                       'events': events.get('items', [])
                   })
               else:
                   logger.error(f"캘린더 {calendar_id}의 이벤트 가져오기 실패: {response.status_code}")
                   logger.error(f"응답 내용: {await response.text()}")  # 에러 응답 내용 로깅
           except Exception as e:
               logger.error(f"캘린더 {calendar_id} 처리 중 오류 발생: {str(e)}")
               continue
   
   return events_all