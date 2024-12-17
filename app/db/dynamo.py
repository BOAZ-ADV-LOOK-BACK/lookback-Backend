import traceback
from app.api.v1.endpoints import google, login
from botocore.exceptions import ClientError
from boto3.dynamodb.types import TypeSerializer
from dotenv import load_dotenv
import boto3
import os
import asyncio
import logging
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()
AWS_ACCESS_kEY_ID = os.environ.get("AWS_ACCESS_kEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
dynamodb_client = boto3.resource('dynamodb',
                            region_name='ap-northeast-2',
                            aws_access_key_id=AWS_ACCESS_kEY_ID,
                            aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

#전체 데이터에서 dynamoDB에서 적재할 데이터 형식으로 변경 
def create_dynamodb_data(user_email, cal_list):
    new_data = {
        'user_id': user_email,  # 파티션 키는 문자열(S)
        'calendar': [           # 리스트(L) 형식의 데이터
            {
                'id': calendar.get("id", ""),
                'summary': calendar.get("summary", ""),
                'description': calendar.get("description", "")
            }
            for calendar in cal_list.get("items", [])  # 빈 값도 안전하게 처리
        ]
    }
    logger.info(f"Transformed data for DynamoDB: {new_data}")
    return new_data

async def get_google_email(access_token):
    url = "https://www.googleapis.com/oauth2/v3/userinfo"

    headers = {
        "Authorization": f"Bearer {access_token}"  # 액세스 토큰을 헤더에 포함
    }
    async with httpx.AsyncClient() as client:  # httpx 사용
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            user_info = response.json()  # 사용자 정보 JSON
            return user_info.get("email")  # 이메일 반환
        else:
            return None
#google_login에서 호출 시 access_token, user_email 가져오기 
async def put_calendar_list(access_token):
    
    token_info = {"access_token": access_token}

    cal_data = await google.get_calendar_data(token_info)
    logger.info("Successfully get calendar data")
    user_email = await get_google_email(access_token)
    #데이터 형식 변경 
    cal_list = create_dynamodb_data(user_email, cal_data)

    #dynamoDB 적재 가능한 데이터 타입으로 변경 
    # cal_list_data = {key: serializer.serialize(value) for key, value in cal_list.items()}

    #캘린더 리스트 데이터 넣기 
    try:
        push_to_dynamodb_calendar_list(cal_list)
    except ClientError as e:
        logger.error(f"ClientError: {e.response['Error']['Message']}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"상세 에러: {traceback.format_exc()}")

# DynamoDB에서 캘린더 리스트 가져오기
async def get_calendar_list_by_user(user_email):
    """유저의 캘린더 리스트를 DynamoDB에서 가져오기"""
    table = dynamodb_client.Table("lookback-calendar-list")
    
    try:
        response = table.get_item(
            Key={
                'user_id': user_email
            }
        )
        return response.get('Item', {}).get('calendar', [])
    except Exception as e:
        logger.error(f"Error getting calendar list from DynamoDB: {str(e)}")
        return []


async def store_calendar_events(user_email, access_token):
    """유저의 모든 캘린더의 이벤트를 가져와서 DynamoDB에 저장"""
    # 1. 캘린더 리스트 가져오기
    calendar_list = await get_calendar_list_by_user(user_email)
    logger.info(f"가져온 캘린더 리스트: {calendar_list}")  # 캘린더리스트 로깅
    
    calendar_ids = [calendar['id'] for calendar in calendar_list]
    logger.info(f"추출된 캘린더 ID 목록: {calendar_ids}") 
    
    # 2. 각 캘린더별로 이벤트 가져오기
    for calendar in calendar_list:
        calendar_id = calendar['id']
        try:
            # Google Calendar API로 이벤트 가져오기
            events = await google.get_calendar_events(access_token, calendar_id)
            
            # DynamoDB에 저장할 형태로 데이터 변환
            events_data = {
                'user_id': user_email,
                'calendar_id': calendar_id,
                'events': [
                    {
                        'event_id': event.get('id'),
                        'summary': event.get('summary'),
                        'description': event.get('description'),
                        'start': event.get('start'),
                        'end': event.get('end'),
                        # 필요한 다른 이벤트 정보들 추가
                    }
                    for event in events.get('items', [])
                ]
            }
            
            # DynamoDB에 저장
            await push_to_dynamodb_events(events_data)
            
        except Exception as e:
            logger.error(f"Error processing calendar {calendar_id}: {str(e)}")
            continue

#DB에 저장할 Item을 파라미터로 입력 받기 
def push_to_dynamodb_calendar_list(dynamodb_item):
    table = dynamodb_client.Table("lookback-calendar-list")  # 테이블 객체 가져오기

    # DynamoDB에 삽입할 데이터
    item = {
        "user_id": dynamodb_item["user_id"],  # 문자열 타입
        "calendar": dynamodb_item["calendar"]  # 리스트 타입
    }

    try:
        table.put_item(Item=item)
        logger.info("Successfully inserted item into DynamoDB")
    except Exception as e:
        logger.error(f"Error inserting item into DynamoDB: {str(e)}")

def push_to_dynamodb_calendar_event(dynamodb_item):
    dynamodb_client.put_item(
            TableName="lookback-db", 
            Item=dynamodb_item
        )
    
async def push_to_dynamodb_events(events_data):
    """이벤트 데이터를 DynamoDB에 저장"""
    table = dynamodb_client.Table("lookback-calendar-events")  # 새로운 테이블 사용
    
    try:
        table.put_item(Item=events_data)
        logger.info(f"Successfully stored events for calendar {events_data['calendar_id']}")
    except Exception as e:
        logger.error(f"Error storing events in DynamoDB: {str(e)}")