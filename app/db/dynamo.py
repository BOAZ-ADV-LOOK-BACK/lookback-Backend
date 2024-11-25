import boto3
import os

load_dotenv()


AWS_ACCESS_kEY_ID = os.environ.get("AWS_ACCESS_kEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")


dynamodb_client = boto3.client('dynamodb',
                              region_name='ap-northeast-2',
                              aws_access_key_id=AWS_ACCESS_kEY_ID,
                              aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

def push_to_dynamodb():
    # DynamoDB에 삽입할 아이템 준비
        dynamodb_item = {
            'calendar_id': {'S': calendar_id},  # 달력 ID
            'event_id': {'S': event_info['id']},  # 이벤트 ID
            'summary': {'S': event_info['summary'] or 'N/A'},  # 이벤트 요약 (없으면 'N/A')
            'start_date': {'S': event_info['start_date'] or 'N/A'},  # 시작 날짜 (없으면 'N/A')
            'end_date': {'S': event_info['end_date'] or 'N/A'},  # 종료 날짜 (없으면 'N/A')
            'start_dateTime': {'S': event_info['start_dateTime'] or 'N/A'},  # 시작 일시 (없으면 'N/A')
            'end_dateTime': {'S': event_info['end_dateTime'] or 'N/A'},  # 종료 일시 (없으면 'N/A')
            'sequence': {'N': str(event_info['sequence'])},  # 시퀀스 번호
            'description': {'S': event_info['description'] or 'N/A'}  # 이벤트 설명 (없으면 'N/A')
        }


        dynamodb_client.put_item(
            TableName="lookback-db", 
            Item=dynamodb_item
        )