from fastapi import APIRouter, HTTPException
from starlette.responses import JSONResponse
from fastapi.responses import RedirectResponse
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from starlette.requests import Request

import json


router = APIRouter()

CLIENT_SECRETS_FILE ='client_secret_639048076528-0mqbo91cf5t0fq5604u0tblqnaka8thp.apps.googleusercontent.com.json'

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
API_SERVICE_NAME = 'calendar'
API_VERSION = 'v3'
REDIRECT_URI = 'http://localhost:8000/auth/callback'

def data_preprocessing(events):
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
            'start_dateTime': item['start'].get('dateTime'),
            'end_dateTime': item['end'].get('dateTime'),
            'sequence': item.get('sequence'),
            'description': item.get('description')
        }
        extracted_info['items'].append(event_info)


    #print(json.dumps(extracted_info, indent=4, ensure_ascii=False))
    with open('processing_test', 'w', encoding='utf-8') as outfile:
        json.dump(extracted_info, outfile, indent=4, ensure_ascii=False)
        
def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
        
@router.get("/calendar")
async def get_calendar(request: Request):
    credentials_info = request.cookies.get('credentials')
    notid_list = ['@gmail.com', 'group.v.calendar.google.com']
    calendar_id = []
    
    if not credentials_info:
        res = RedirectResponse(url='/auth/auth')
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
        
        response = RedirectResponse(url='/auth/auth')
        response.delete_cookie('credentials')
        return response
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"An error occurred: {str(e)}")
    