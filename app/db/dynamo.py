from app.api.v1.endpoints import google, login
from botocore.exceptions import ClientError
from boto3.dynamodb.types import TypeSerializer
from dotenv import load_dotenv

import boto3
import os
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

AWS_ACCESS_kEY_ID = os.environ.get("AWS_ACCESS_kEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")


dynamodb_client = boto3.client('dynamodb',
                            region_name='ap-northeast-2',
                            aws_access_key_id=AWS_ACCESS_kEY_ID,
                            aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

#전체 데이터에서 dynamoDB에서 적재할 데이터 형식으로 변경 
def create_dynamodb_data(user_email, cal_list):
    
    new_data = {
        'user_id': user_email,
        "calendar":[
            {
                'id': calendar["id"],
                "summary": calendar["summary"],
                "description": calendar["description"]
            
            }
            
            for calendar in cal_list["calendars"]
        ]
    }
    
    return new_data


#google_login에서 호출 시 access_token, user_email 가져오기 
def put_calendar_list(access_token, user_email):
    
    #dynamoDB에 넣을 수 있는 객체로 변환하기 위한 typeSerializer 객체 생성 
    serializer = TypeSerializer()
    
    #캘린더 리스트 가져오기 -> 문제 발생 가능 지점 
    loop = asyncio.get_event_loop()
    cal_data = loop.run_until_complete(google.get_calendar_data(access_token))
    logger.info("Successfully get calendar data")

    #데이터 형식 변경 
    cal_list = create_dynamodb_data(user_email, cal_data)
    
    #dynamoDB 적재 가능한 데이터 타입으로 변경 
    cal_list_data = {key: serializer.serialize(value) for key, value in cal_list.items()}
    
    
    #캘린더 리스트 데이터 넣기 
    try:
        push_to_dynamodb_calendar_list(cal_list_data)
        logger.info("Successfully pushed calendar list data for user")
    except ClientError as e:
        logger.error("Error saving calendar list")
    except Exception as e:
        logger.error("Unexpected error saving calendar list for user")
    

#def put_calendar_events():
    
    #토큰 받아오기
    
    #캘린더 리스트 받아오기
    #cal_list = google.get_calendar_data(access_toekn)
    
    #캘린더 id로 순회하면서 데이터 가져오기 -> 전처리 후 DB
    #for event_list in cal_list["calendar"]["id"]:
        
    
    
    
#DB에 저장할 Item을 파라미터로 입력 받기 
def push_to_dynamodb_calendar_list(dynamodb_item):
        dynamodb_client.put_item(
            TableName="lookback-calendar-list", 
            Item=dynamodb_item
        )

def push_to_dynamodb_calendar_event(dynamodb_item):
    dynamodb_client.put_item(
            TableName="lookback-db", 
            Item=dynamodb_item
        )