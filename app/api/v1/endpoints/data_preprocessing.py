from fastapi import APIRouter, HTTPException
from starlette.responses import JSONResponse
from fastapi.responses import RedirectResponse
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from starlette.requests import Request

import os
import json
import boto3
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()

AWS_ACCESS_kEY_ID = os.environ.get("AWS_ACCESS_kEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")


CLIENT_SECRETS_FILE ='client_secret_639048076528-0mqbo91cf5t0fq5604u0tblqnaka8thp.apps.googleusercontent.com.json'

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
API_SERVICE_NAME = 'calendar'
API_VERSION = 'v3'
REDIRECT_URI = 'https://api.look-back.site/api/v1/save-token'



dynamodb_client = boto3.client('dynamodb',
                              region_name='ap-northeast-2',
                              aws_access_key_id=AWS_ACCESS_kEY_ID,
                              aws_secret_access_key=AWS_SECRET_ACCESS_KEY)



def data_preprocessing(events, calendar_id):
    data = events
    
    extracted_info = {
    'summary': data.get('summary'),
    'description': data.get('description'),
    'updated': data.get('updated'),
    'items': []
    }
    
    for item in data.get('items', []):
        event_info = {
        'id': item.get('id'),
        'summary': item.get('summary'),
        'start_date': None,
        'end_date': None,
        'start_dateTime': None,
        'end_dateTime': None,
        'sequence': item.get('sequence'),
        'description': item.get('description')
    }

        # start와 end에서 date 또는 dateTime 처리
        if 'date' in item['start']:  # date가 있을 경우
            event_info['start_date'] = item['start'].get('date')
            event_info['end_date'] = (datetime.strptime(item['end'].get('date'), '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'dateTime' in item['start']:  # dateTime이 있을 경우
            event_info['start_dateTime'] = item['start'].get('dateTime')
            event_info['end_dateTime'] = item['end'].get('dateTime')

            # dateTime에서 날짜만 추출하여 date로 저장
            event_info['start_date'] = event_info['start_dateTime'][:10]
            event_info['end_date'] = event_info['end_dateTime'][:10]
            
            if event_info['end_dateTime'].endswith("T00:00:00+09:00") or event_info['end_dateTime'].endswith("T00:00:00Z"):
                # end_dateTime을 전날 23:59:59로 변경
                event_info['end_dateTime'] = (datetime.strptime(event_info['end_date'], '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%dT23:59:59+09:00')
                # end_date도 전날로 변경
                event_info['end_date'] = (datetime.strptime(event_info['end_date'], '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')

        extracted_info['items'].append(event_info)

    

        dynamodb_item = {
            'calendar_id': {'S': calendar_id},  
            'event_id': {'S': event_info['id']},  
            'summary': {'S': event_info['summary'] or 'N/A'},
            'start_date': {'S': event_info['start_date'] or 'N/A'},
            'end_date': {'S': event_info['end_date'] or 'N/A'},
            'start_dateTime': {'S': event_info['start_dateTime'] or 'N/A'},
            'end_dateTime': {'S': event_info['end_dateTime'] or 'N/A'},
            'sequence': {'N': str(event_info['sequence'])},
            'description': {'S': event_info['description'] or 'N/A'}
        }


        dynamodb_client.put_item(
            TableName="lookback-db", 
            Item=dynamodb_item
        )
    
      
        
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
    