from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Union
import httpx
import json
import logging

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_access_token(code: str) -> dict:
   """
   Google OAuth2 인증 코드를 사용하여 액세스 토큰을 요청합니다.

   Args:
       code (str): Google OAuth2 인증 코드

   Returns:
       dict: 액세스 토큰 정보가 포함된 딕셔너리
             (access_token, token_type, expires_in 등의 키를 포함)
   """
   token_url = "https://oauth2.googleapis.com/token"
   
   with open("client_secret_639048076528-0mqbo91cf5t0fq5604u0tblqnaka8thp.apps.googleusercontent.com.json", "r") as f:
       client_config = json.load(f)["web"]

   token_data = {
       "code": code,
       "client_id": client_config["client_id"],
       "client_secret": client_config["client_secret"],
       "redirect_uri": "postmessage",
       "grant_type": "authorization_code",
   }

   async with httpx.AsyncClient() as client:
       response = await client.post(token_url, data=token_data)
       return response.json()

@router.get("/calendar-list")
async def get_calendar_data(token_info: dict) -> dict:
   """
   사용자의 Google Calendar 목록을 조회합니다.

   Args:
       token_info (dict): 액세스 토큰 정보가 포함된 딕셔너리

   Returns:
       dict: 사용자의 캘린더 목록 정보
   """
   async with httpx.AsyncClient() as client:
       response = await client.get(
           "https://www.googleapis.com/calendar/v3/users/me/calendarList",
           headers={"Authorization": f"Bearer {token_info['access_token']}"}
       )
       response.raise_for_status()
       return response.json()

async def get_calendar_events(access_token: str, calendar_ids: Union[str, list]) -> list:
   """
   지정된 캘린더들의 이벤트를 조회합니다.

   Args:
       access_token (str): Google Calendar API 접근을 위한 액세스 토큰
       calendar_ids (Union[str, list]): 단일 캘린더 ID 또는 캘린더 ID 목록

   Returns:
       list: 각 캘린더의 이벤트 정보를 포함한 리스트
             [{'calendar_id': str, 'events': list}, ...]
   """
   if isinstance(calendar_ids, str):
       calendar_ids = [calendar_ids]
   
   logger.info(f"받은 캘린더 ID 목록: {calendar_ids}")
   events_all = []
   
   async with httpx.AsyncClient() as client:
       for calendar_id in calendar_ids:
           logger.info(f"처리 중인 캘린더 ID: {calendar_id}")
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
           except Exception as e:
               logger.error(f"캘린더 {calendar_id} 처리 중 오류 발생: {str(e)}")
               continue
   
   return events_all