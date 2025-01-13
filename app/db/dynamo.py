# dynamo.py
import json
import traceback

import pytz
from app.api.v1.endpoints import google, login
from botocore.exceptions import ClientError
from boto3.dynamodb.types import TypeSerializer
from app.api.v1.endpoints.google import get_calendar_events
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
dynamodb_client = boto3.resource(
   'dynamodb',
   region_name='ap-northeast-2',
   aws_access_key_id=AWS_ACCESS_kEY_ID,
   aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

def create_dynamodb_data(user_email: str, cal_list: dict) -> dict:
   """
   사용자의 캘린더 리스트를 DynamoDB 형식으로 변환합니다.

   Args:
       user_email (str): 사용자 이메일
       cal_list (dict): Google Calendar API로부터 받은 캘린더 리스트

   Returns:
       dict: DynamoDB 형식으로 변환된 데이터
   """
   new_data = {
       'user_id': user_email,
       'calendar': [
           {
               'id': calendar.get("id", ""),
               'summary': calendar.get("summary", ""),
               'description': calendar.get("description", "")
           }
           for calendar in cal_list.get("items", [])
       ]
   }
   logger.info(f"Transformed data for DynamoDB: {new_data}")
   return new_data

async def get_google_email(access_token: str) -> str:
   """
   Google OAuth2 액세스 토큰을 사용하여 사용자 이메일을 조회합니다.

   Args:
       access_token (str): Google OAuth2 액세스 토큰

   Returns:
       str: 사용자 이메일 또는 None (조회 실패 시)
   """
   url = "https://www.googleapis.com/oauth2/v3/userinfo"
   headers = {"Authorization": f"Bearer {access_token}"}
   
   async with httpx.AsyncClient() as client:
       response = await client.get(url, headers=headers)
       if response.status_code == 200:
           user_info = response.json()
           return user_info.get("email")
       return None

async def put_calendar_list(access_token: str):
   """
   사용자의 Google 캘린더 리스트를 조회하여 DynamoDB에 저장합니다.

   Args:
       access_token (str): Google OAuth2 액세스 토큰
   """
   token_info = {"access_token": access_token}
   cal_data = await google.get_calendar_data(token_info)
   logger.info("Successfully get calendar data")
   
   user_email = await get_google_email(access_token)
   cal_list = create_dynamodb_data(user_email, cal_data)

   try:
       push_to_dynamodb_calendar_list(cal_list)
   except ClientError as e:
       logger.error(f"ClientError: {e.response['Error']['Message']}")
   except Exception as e:
       logger.error(f"Unexpected error: {str(e)}")
       logger.error(f"상세 에러: {traceback.format_exc()}")

async def get_calendar_list_by_user(user_email: str) -> list:
   """
   DynamoDB에서 사용자의 캘린더 리스트를 조회합니다.

   Args:
       user_email (str): 사용자 이메일

   Returns:
       list: 캘린더 리스트 또는 빈 리스트 (조회 실패 시)
   """
   table = dynamodb_client.Table("lookback-calendar-list")
   
   try:
       response = table.get_item(Key={'user_id': user_email})
       return response.get('Item', {}).get('calendar', [])
   except Exception as e:
       logger.error(f"Error getting calendar list from DynamoDB: {str(e)}")
       return []

async def store_calendar_events(user_email: str, access_token: str):
    """
    사용자의 모든 캘린더에 대한 이벤트를 조회하여 DynamoDB에 저장합니다.
    먼저 사용자의 기존 데이터를 삭제한 후 새로운 데이터를 저장합니다.

    Args:
        user_email (str): 사용자 이메일
        access_token (str): Google OAuth2 액세스 토큰
    """
    table = dynamodb_client.Table("lookback-calendar-events")
    
    try:
        # 1. 먼저 사용자의 기존 데이터를 모두 삭제
        response = table.query(
            KeyConditionExpression='user_id = :uid',
            ExpressionAttributeValues={
                ':uid': user_email
            }
        )
        
        with table.batch_writer() as batch:
            for item in response.get('Items', []):
                batch.delete_item(
                    Key={
                        'user_id': item['user_id'],
                        'calendar_id': item['calendar_id']
                    }
                )
        logger.info(f"사용자 {user_email}의 기존 데이터 삭제 완료")
        
        # 2. 새로운 데이터 저장 프로세스
        calendar_list = await get_calendar_list_by_user(user_email)
        
        for calendar in calendar_list:
            try:
                calendar_id = calendar['id']
                logger.info(f"캘린더 {calendar_id} 이벤트 처리 시작")
                
                events = await get_calendar_events(access_token, [calendar_id])
                if events and events[0]['events']:
                    events_data = {
                        'user_id': user_email,
                        'calendar_id': calendar_id,
                        'events': events[0]['events']
                    }
                    
                    await push_to_dynamodb_events(events_data)
                    logger.info(f"캘린더 {calendar_id} 이벤트 저장 완료")
                else:
                    logger.info(f"캘린더 {calendar_id}에 저장할 이벤트가 없습니다")
            except Exception as e:
                logger.error(f"캘린더 {calendar_id} 처리 중 오류 발생: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"전체 프로세스 중 오류 발생: {str(e)}")
        logger.error(f"상세 오류: {traceback.format_exc()}")

def push_to_dynamodb_calendar_list(dynamodb_item: dict):
   """
   캘린더 리스트를 DynamoDB에 저장합니다.

   Args:
       dynamodb_item (dict): 저장할 캘린더 리스트 데이터
   """
   table = dynamodb_client.Table("lookback-calendar-list")
   item = {
       "user_id": dynamodb_item["user_id"],
       "calendar": dynamodb_item["calendar"]
   }

   try:
       table.put_item(Item=item)
       logger.info("Successfully inserted item into DynamoDB")
   except Exception as e:
       logger.error(f"Error inserting item into DynamoDB: {str(e)}")

async def push_to_dynamodb_events(events_data: dict):
   """
   캘린더 이벤트를 DynamoDB에 저장합니다.

   Args:
       events_data (dict): 저장할 이벤트 데이터
   """
   table = dynamodb_client.Table("lookback-calendar-events")
   
   try:
       table.put_item(Item=events_data)
       logger.info(f"Successfully stored events for calendar {events_data['calendar_id']}")
   except Exception as e:
       logger.error(f"Error storing events in DynamoDB: {str(e)}")


from datetime import datetime, timedelta

# 사용자 별로 미리 필터링해서 데이터 가져오기
async def get_weekly_activity_data_per_user(user_email: str) -> dict:
    table = dynamodb_client.Table("lookback-calendar-events")
    
    try:
        # 1. 조회 기간 설정
        today = datetime.now(pytz.UTC)
        this_week_start = today - timedelta(days=today.weekday())
        this_week_end = this_week_start + timedelta(days=5)
        
        this_week_start = this_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        this_week_end = this_week_end.replace(hour=23, minute=59, second=59)

        logger.info(f"[조회 기간] {this_week_start.strftime('%Y-%m-%d %H:%M')} ~ {this_week_end.strftime('%Y-%m-%d %H:%M')}")

        # 2. 데이터 조회
        response = table.query(
            KeyConditionExpression=Key('user_id').eq(user_email)
        )
        raw_events = response.get('Item', [])
        logger.info(f"[전체 데이터 수] {len(raw_events)}개")
        # logger.info(f"[데이터 구조 확인] {raw_events[:1]}")  # 첫 번째 데이터의 구조 확인
        
        # 3. 조회 기간에 해당하는 데이터만 필터링
        filtered_events = []
        for event in raw_events:
            try:
                if 'events' in event:  # events 배열이 있는 경우
                    for sub_event in event['events']:
                        if 'start' in sub_event and 'dateTime' in sub_event['start']:
                            event_time = datetime.fromisoformat(sub_event['start']['dateTime'])
                            if this_week_start <= event_time <= this_week_end:
                                filtered_events.append(sub_event)
            except Exception as sub_e:
                logger.error(f"이벤트 처리 중 오류: {str(sub_e)}")
                continue
                
        logger.info(f"[필터링 후 데이터 수] {len(filtered_events)}개")
        logger.info(f"[필터링 된 데이터 샘플]\n{filtered_events[:2]}")  # 처음 2개만 로깅
        
        return {
            'events': filtered_events,
            'this_week_start': this_week_start.isoformat()
        }
        
    except Exception as e:
        logger.error(f"조회 중 오류: {str(e)}")
        logger.error(f"전체 오류 내용: {traceback.format_exc()}")
        return {'events': [], 'this_week_start': None}

async def get_weekly_activity_data(user_email: str) -> dict:
    table = dynamodb_client.Table("lookback-calendar-events")
    
    try:
        # 1. 조회 기간 설정
        today = datetime.now(pytz.UTC)
        this_week_start = today - timedelta(days=today.weekday())
        this_week_end = this_week_start + timedelta(days=5)
        
        this_week_start = this_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        this_week_end = this_week_end.replace(hour=23, minute=59, second=59)

        logger.info(f"[조회 기간] {this_week_start.strftime('%Y-%m-%d %H:%M')} ~ {this_week_end.strftime('%Y-%m-%d %H:%M')}")

        # 2. 데이터 조회
        response = table.scan()
        raw_events = response.get('Items', [])
        logger.info(f"[전체 데이터 수] {len(raw_events)}개")
        # logger.info(f"[데이터 구조 확인] {raw_events[:1]}")  # 첫 번째 데이터의 구조 확인
        
        # 3. 조회 기간에 해당하는 데이터만 필터링
        filtered_events = []
        for event in raw_events:
            try:
                if 'events' in event:  # events 배열이 있는 경우
                    for sub_event in event['events']:
                        if 'start' in sub_event and 'dateTime' in sub_event['start']:
                            event_time = datetime.fromisoformat(sub_event['start']['dateTime'])
                            if this_week_start <= event_time <= this_week_end:
                                filtered_events.append(sub_event)
            except Exception as sub_e:
                logger.error(f"이벤트 처리 중 오류: {str(sub_e)}")
                continue
                
        logger.info(f"[필터링 후 데이터 수] {len(filtered_events)}개")
        logger.info(f"[필터링 된 데이터 샘플]\n{filtered_events[:2]}")  # 처음 2개만 로깅
        
        return {
            'events': filtered_events,
            'this_week_start': this_week_start.isoformat()
        }
        
    except Exception as e:
        logger.error(f"조회 중 오류: {str(e)}")
        logger.error(f"전체 오류 내용: {traceback.format_exc()}")
        return {'events': [], 'this_week_start': None}

async def check_calendar_events(user_email: str):
    """
    사용자의 캘린더 이벤트 데이터를 확인하는 함수
    """
    table = dynamodb_client.Table("lookback-calendar-events")
    
    try:
        response = table.query(
            KeyConditionExpression='user_id = :uid',
            ExpressionAttributeValues={':uid': user_email}
        )
        
        logger.info("=== 캘린더 이벤트 데이터 확인 ===")
        logger.info(f"총 아이템 수: {len(response.get('Items', []))}")
        
        for item in response.get('Items', []):
            logger.info(f"\n캘린더 ID: {item.get('calendar_id')}")
            events = item.get('events', [])
            logger.info(f"이벤트 수: {len(events)}")
            
            # 처음 5개 이벤트만 샘플로 출력
            for event in events[:5]:
                logger.info(f"""
                제목: {event.get('summary')}
                시작: {event.get('start', {}).get('dateTime')}
                종료: {event.get('end', {}).get('dateTime')}
                """)
                
        return response.get('Items', [])
        
    except Exception as e:
        logger.error(f"데이터 확인 중 오류 발생: {str(e)}")
        return []