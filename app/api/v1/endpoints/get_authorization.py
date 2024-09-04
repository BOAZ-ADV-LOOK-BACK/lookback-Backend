from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from starlette.requests import Request
import json

router = APIRouter()

CLIENT_SECRETS_FILE = 'client_secret_639048076528-0mqbo91cf5t0fq5604u0tblqnaka8thp.apps.googleusercontent.com.json'

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
API_SERVICE_NAME = 'calendar'
API_VERSION = 'v3'
REDIRECT_URI = 'http://localhost:8000/auth/callback'
#REDIRECT_URI='https://look-back.site/auth/callback'

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

@router.get("/auth")
async def auth():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    authorization_url, state = flow.authorization_url(access_type='offline')
    return RedirectResponse(url=authorization_url)

@router.get("/callback")
async def auth_callback(request: Request):
    state = request.query_params.get('state')
    code = request.query_params.get('code')
    
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        state = state
    )
    
    authorization_response = str(request.url)
    flow.fetch_token(authorization_response=authorization_response )
    
    if not flow.credentials:
        raise HTTPException(status_code=400, detail="Failed to fetch token")
    
    credentials = flow.credentials
    
    response = RedirectResponse(url='/preprocess/calendar')
    response.set_cookie(key='credentials', value=json.dumps(credentials_to_dict(credentials)), httponly=True)
    
    return response
