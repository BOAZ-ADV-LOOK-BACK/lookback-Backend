from fastapi import APIRouter, HTTPException
from starlette.responses import JSONResponse
from fastapi.responses import RedirectResponse
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from starlette.requests import Request

import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()




CLIENT_SECRETS_FILE ='client_secret_639048076528-0mqbo91cf5t0fq5604u0tblqnaka8thp.apps.googleusercontent.com.json'

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
API_SERVICE_NAME = 'calendar'
API_VERSION = 'v3'
REDIRECT_URI = 'https://api.look-back.site/api/v1/save-token'





def data_preprocessing(events, calendar_id):
    # 받은 events 데이터를 'data' 변수에 할당
    data = events
    
    # 데이터에서 추출할 정보 초기화
    extracted_info = {
        'summary': data.get('summary'),  # 이벤트의 요약 정보
        'description': data.get('description'),  # 이벤트의 설명
        'updated': data.get('updated'),  # 마지막 업데이트 정보
        'items': []  # 각 이벤트 아이템을 담을 리스트
    }
    
    # 이벤트 항목을 하나씩 순회
    for item in data.get('items', []):
        event_info = {
            'id': item.get('id'),  # 이벤트 ID
            'summary': item.get('summary'),  # 이벤트 요약
            'start_date': None,  # 시작 날짜
            'end_date': None,  # 종료 날짜
            'start_dateTime': None,  # 시작 일시
            'end_dateTime': None,  # 종료 일시
            'sequence': item.get('sequence'),  # 이벤트 시퀀스 (수정된 순서)
            'description': item.get('description')  # 이벤트 설명
        }

        # 이벤트의 시작 시간이 날짜만 있는 경우와 날짜 및 시간이 있는 경우를 구분하여 처리
        if 'date' in item['start']:  # 날짜만 있는 경우
            event_info['start_date'] = item['start'].get('date')  # 시작 날짜
            event_info['end_date'] = (datetime.strptime(item['end'].get('date'), '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')  # 종료 날짜 (1일 이전으로 설정)
        elif 'dateTime' in item['start']:  # 날짜 및 시간이 있는 경우
            event_info['start_dateTime'] = item['start'].get('dateTime')  # 시작 일시
            event_info['end_dateTime'] = item['end'].get('dateTime')  # 종료 일시

            # 'dateTime' 정보에서 날짜 부분을 추출하여 'start_date'와 'end_date'에 설정
            event_info['start_date'] = event_info['start_dateTime'][:10]  # 시작 날짜
            event_info['end_date'] = event_info['end_dateTime'][:10]  # 종료 날짜
            
            # 만약 종료 일시가 자정(23:59:59)인 경우, 종료 날짜를 하루 전날의 자정으로 설정
            if event_info['end_dateTime'].endswith("T00:00:00+09:00") or event_info['end_dateTime'].endswith("T00:00:00Z"):
                event_info['end_dateTime'] = (datetime.strptime(event_info['end_date'], '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%dT23:59:59+09:00')
                event_info['end_date'] = (datetime.strptime(event_info['end_date'], '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')

        # 추출된 이벤트 정보를 'extracted_info'에 추가
        extracted_info['items'].append(event_info)

        
    
      
        
def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
#        'refresh_token': credentials.refresh_token,
#        'token_uri': credentials.token_uri,
#        'client_id': credentials.client_id,
#        'client_secret': credentials.client_secret,
#        'scopes': credentials.scopes
    }

@router.get("/calendar")
async def get_calendar(request: Request):
    credentials_info = request.cookies.get('credentials')
    notid_list = ['@gmail.com', 'group.v.calendar.google.com']
    calendar_id = []
    
    if not credentials_info:
        res = RedirectResponse(url='/api/v1/save-token')
        return res
    
    try:
        credentials = json.loads(credentials_info)
        creds = Credentials.from_authorized_user_info(info=credentials, scopes=SCOPES)
        cal = build('calendar', 'v3', credentials=creds)
        
        page_token = None
        
        while True:
            calendar_list = cal.calendarList().list(pageToken=page_token).execute()
            for cal_details in calendar_list['items']:
                cal_id = cal_details['id']
                
                if any (i in cal_id for i in notid_list):
                    continue
                
                calendar_id.append(cal_id)

            if not page_token:
                break
            
        
        if calendar_id:
            event_results = cal.events().list(calendarId = calendar_id[1] , maxResults=10).execute()
            events = event_results.get('items', [])
        
        data_preprocessing(event_results)
        response = JSONResponse(content={"events": events})
        response.set_cookie(key='credentials', value=json.dumps(credentials), httponly=True)
            
        return response
    
    except RefreshError:
        
        response = RedirectResponse(url='/api/v1/save-token')
        response.delete_cookie('credentials')
        return response
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"An error occurred: {str(e)}")
    