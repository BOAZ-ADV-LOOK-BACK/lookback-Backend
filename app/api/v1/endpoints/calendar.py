# 캘린더 관련 API 모음
# calender.py
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import pytz
from app.api.v1.endpoints import login, users, google, calendar 
from app.api.deps import get_current_user
from app.db.dynamo import *
from app.models.user import User
import httpx
import json
import logging
import traceback

# calendar.py 전용 로거 설정
calendar_logger = logging.getLogger('calendar')
calendar_logger.setLevel(logging.INFO)

# 파일 핸들러 추가
file_handler = logging.FileHandler('calendar.log')
file_handler.setLevel(logging.INFO)

# 스트림 핸들러 추가 
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)

# 포맷터 설정 - calendar.py용 특별 포맷
formatter = logging.Formatter('[캘린더 API] %(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

calendar_logger.addHandler(file_handler)
calendar_logger.addHandler(stream_handler)

# API 라우터 설정

router = APIRouter()

async def refresh_google_token(refresh_token: str):
   calendar_logger.info("구글 토큰 갱신 프로세스 시작")
   
   try:
       # client secrets 파일 읽기
       calendar_logger.info("클라이언트 설정 파일 읽기 시작")
       with open("client_secret_639048076528-0mqbo91cf5t0fq5604u0tblqnaka8thp.apps.googleusercontent.com.json", "r") as f:
           client_config = json.load(f)["web"]
       calendar_logger.info("클라이언트 설정 파일 읽기 완료")

       # 요청 데이터 준비
       token_data = {
           "client_id": client_config["client_id"],
           "client_secret": client_config["client_secret"],
           "refresh_token": refresh_token,
           "grant_type": "refresh_token"
       }
       calendar_logger.info("토큰 갱신 요청 데이터 준비 완료")

       async with httpx.AsyncClient() as client:
           calendar_logger.info("구글 토큰 갱신 요청 시작")
           response = await client.post("https://oauth2.googleapis.com/token", data=token_data)
           response.raise_for_status()
           
           token_info = response.json()
           calendar_logger.info("구글 토큰 갱신 응답 수신 완료")
           
           if "access_token" not in token_info:
               calendar_logger.error("응답에 access_token이 없음")
               raise HTTPException(
                   status_code=400,
                   detail="액세스 토큰 갱신 실패"
               )
               
           calendar_logger.info("새로운 액세스 토큰 발급 성공")
           return token_info["access_token"]
           
   except httpx.HTTPError as e:
       calendar_logger.error(f"구글 토큰 갱신 중 HTTP 에러 발생: {str(e)}")
       calendar_logger.error(f"상세 에러: {traceback.format_exc()}")
       raise HTTPException(
           status_code=500,
           detail="구글 액세스 토큰 갱신 실패"
       )
   except Exception as e:
       calendar_logger.error(f"토큰 갱신 중 예상치 못한 에러 발생: {str(e)}")
       calendar_logger.error(f"상세 에러: {traceback.format_exc()}")
       raise HTTPException(
           status_code=500,
           detail="토큰 갱신 중 내부 서버 오류 발생"
       )

@router.post("/sync-calendar")
async def sync_calendar(current_user: User = Depends(get_current_user)):
   calendar_logger.info("캘린더 동기화 시작")
   try:
       calendar_logger.info(f"사용자 {current_user.email}의 캘린더 동기화 요청")
       
       # refresh token으로 새 access token 획득
       calendar_logger.info("새로운 액세스 토큰 요청")
       new_access_token = await refresh_google_token(current_user.refresh_token)
       calendar_logger.info("새로운 액세스 토큰 발급 완료")
       
       # 캘린더 동기화
       calendar_logger.info("DynamoDB에 캘린더 데이터 동기화 시작")
       await put_calendar_list(new_access_token)
       calendar_logger.info("캘린더 데이터 동기화 완료")
       
       return {
           "success": True,
           "message": "캘린더 동기화가 성공적으로 완료되었습니다"
       }
   except Exception as e:
       calendar_logger.error(f"캘린더 동기화 중 오류 발생: {str(e)}")
       calendar_logger.error(f"상세 에러 정보: {traceback.format_exc()}")
       raise HTTPException(
           status_code=500, 
           detail=f"캘린더 동기화 실패: {str(e)}"
       )

@router.post("/sync-events")
async def sync_events(current_user: User = Depends(get_current_user)):
    calendar_logger.info("이벤트 동기화 시작")
    try:
        calendar_logger.info(f"사용자 {current_user.email}의 이벤트 동기화 요청")
        
        # refresh token으로 새 access token 획득
        calendar_logger.info("새로운 액세스 토큰 요청")
        new_access_token = await refresh_google_token(current_user.refresh_token)
        calendar_logger.info("새로운 액세스 토큰 발급 완료")
        
        # 이벤트 동기화 (기존에 만든 함수 사용)
        calendar_logger.info("DynamoDB에 이벤트 데이터 동기화 시작")
        await store_calendar_events(current_user.email, new_access_token)
        calendar_logger.info("이벤트 데이터 동기화 완료")
        
        return {
            "success": True,
            "message": "이벤트 동기화가 성공적으로 완료되었습니다"
        }
    except Exception as e:
        calendar_logger.error(f"이벤트 동기화 중 오류 발생: {str(e)}")
        calendar_logger.error(f"상세 에러 정보: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"이벤트 동기화 실패: {str(e)}"
        )
    
### 캘린더 API
# 1. 캘린더 데이터 요청
# 2. 전처리
# 3. dynamodb에 비동기로 삽입
# 4. 프론트로 데이터 return

@router.get("/dashboard-data")
async def get_dashboard_data(code):
    # token_info 예시는 print 후 확인 요망
    token_info = await google.get_access_token(code)


    # 1. 캘린더 데이터 요청
    calendar_data_origin = await google.get_calendar_data(code)

    # 2. 전처리
    # data_preprocessing.py 내부 함수 참고

    # 3. dynamodb 비동기 삽입
    # data_preprocessing.py 내부 함수 참고
    
    # 4. 프론트로 리턴
    # 2번에서 전처리 한 결과 리턴해주면 됨
    # 향후 프론트에서 이 데이터 받아서 알아서 잘 각 시각화 component에 잘 매핑

#캘린더 별 활동 시간 API
@router.post("/dashboard-spendingTime")
async def get_spending_time_of_sum(current_user: User = Depends(get_current_user)):

    duration_by_calendar = await sum_time_by_calendar(current_user.email)
    
    calendar_logger.info(f"캘린더별 활동 시간 확인 완료:{duration_by_calendar}")

    return {"success": True, "spendingTime": duration_by_calendar}

async def sum_time_by_calendar(user):
    
    user_duration_time = {}
    
    # 사용자 캘린더 리스트 가져오기 
    user_cal_list = await get_calendar_list_by_user(user)
    
    calendar_logger.info(f"사용자 캘린더 리스트 가져오기 성공: {user_cal_list}")
    
    for calendar in user_cal_list:
        summary = calendar['summary']
        cal_id = calendar['id']
        user_duration_time[summary] = await get_user_event(user, cal_id)
    
    return user_duration_time


#upcomming scheduleAPI
@router.post('/dashboard-upcomming-schedule')
async def user_upcomming_events(current_user: User = Depends(get_current_user)):
    
    user_upcomming_evnets_list = await upcomming_event_dict(current_user.email)
    
    calendar_logger.info(f"곧 다가오는 스케줄: {user_upcomming_evnets_list}")
    
    return {"success": True, "upcommingList": user_upcomming_evnets_list}
    

# 갓생지수 API
@router.post("/dashboard-godLifeBar")
async def get_godLife_bar(current_user: User = Depends(get_current_user)):
    calendar_logger.info("갓생지수 데이터 로딩 시작...")
    
    # 활동 데이터 가져오기
    processed_data = await get_weekly_activity(current_user)
    if not processed_data.get("success"):
        calendar_logger.error("갓생지수를 가져오는데 실패했습니다.")
        return {"success": False, "message": "Failed to fetch godLife data"}

    calendar_logger.info("갓생지수 데이터 로딩 완료...")

    # 갓생지수 계산    
    godLifeidx = godLifeIndex(processed_data.get("data", []))
    calendar_logger.info(f"갓생지수: {godLifeidx}")
    if godLifeidx < 4:
        calendar_logger.info("갓생이 아닙니다.")
        return {"success": True, "godLifeBar": 0}

    calendar_logger.info("갓생지수 데이터 전송 완료...")
    
    # 갓생지수 퍼센트 반환
    godLifePercent = godLifeidx / 7 * 100
    return {"success": True, "godLifeIdx": godLifePercent}


## 갓생지수 판정 함수
def godLifeIndex(weekly_data: dict) -> int:
    """
    일주일 중 하루의 총 이벤트 시간이 6시간 이상인 요일 횟수를 반환, 4번 이상일 경우 갓생
    
    Args:
        weekly_data (dict): process_weekly_activity_data 함수의 결과 데이터.
    
    Returns:
        bool: 조건을 만족하면 True, 아니면 False.
    """
    try:
        days_with_long_events = 0
        
        for day_data in weekly_data.get('this_week', []):
            start_time = day_data.get('startTime', 0)
            end_time = day_data.get('endTime', 0)
            if end_time - start_time > 6.0:
                days_with_long_events += 1
        
        return days_with_long_events
    except Exception as e:
        print(f"Error processing workload: {e}")
        return False

@router.post("/dashboard-category-dist")
async def get_category(current_user: User = Depends(get_current_user)):
    """
    내 캘린더의 이벤트 수가 가장 많은 순으로 상위 6개의 캘린더 나열

    예시 데이터:
    const exampleCategoryDistribution = {
        "success": true,
        "categories": [
            { "category": "Work", "entry_number": 35 , "summary": "예예"},
            { "category": "Exercise", "entry_number": 20 , "summary": "예예"},
            { "category": "Study", "entry_number": 15 , "summary": "예예"},
            { "category": "Leisure", "entry_number": 10 , "summary": "예예"},
            { "category": "Social", "entry_number": 8 , "summary": "예예"},
            { "category": "Other", "entry_number": 5 , "summary": "예예"}
        ]
    }

    """
    
    try:
        calendar_logger.info("카테고리 분포 데이터 로딩 시작...")

        # 1. 캘린더 리스트 가져오기
        cal_list = await get_calendar_list_by_user(current_user.email)
        calendar_logger.info(f"cal_list 구조: {cal_list}")

        # 캘린더 리스트에서 id와 summary 추출하여 calendar_ids 딕셔너리 생성
        calendar_ids = {item['id']: item['summary'] for item in cal_list}
        # 각 calendar_id는 처음에 0으로 카운트를 설정
        event_count = {item['id']: 0 for item in cal_list}
        calendar_logger.info(f"`cal_list`의 ID와 summary 추출 결과: {calendar_ids}")

        # 2. 이벤트 데이터 가져오기
        processed_data = await get_weekly_activity_data_per_user(current_user.email)
        events = processed_data.get('events', [])
        calendar_logger.info(f"주간 활동 데이터: {len(events)}개의 이벤트")

        if not events:
            calendar_logger.info("주간 활동 데이터가 없습니다.")

        # 3. 이벤트 데이터에서 캘린더별로 개수 세기
        for event in events:
            try:
                event_id = event['organizer']['email']  # event에서 직접 email 접근
                if event_id in event_count:
                    event_count[event_id] += 1
                else:
                    # 존재하지 않는 이벤트가 있을 경우, 추가하여 카운트 시작
                    event_count[event_id] = 1
            except KeyError as e:
                calendar_logger.error(f"이벤트 처리 중 KeyError 발생: {str(e)}")
                continue
            except Exception as e:
                calendar_logger.error(f"이벤트 처리 중 예기치 않은 오류 발생: {str(e)}")
                continue

        # 4. 데이터 정리 (상위 6개 추출)
        sorted_categories = sorted(event_count.items(), key=lambda x: x[1], reverse=True)[:6]

        # 5. 카테고리 분포 데이터 구성 (cal_id, summary, entry_number 포함)
        category_distribution = [
            {
                "category": cal_id,
                "summary": calendar_ids.get(cal_id, "정보 없음"),  # summary가 없을 경우 '정보 없음'으로 처리
                "entry_number": count
            }
            for cal_id, count in sorted_categories
        ]

        calendar_logger.info(f"카테고리 분포 데이터: {json.dumps(category_distribution, ensure_ascii=False)}")

        # 6. 최종 데이터 반환
        return {
            "success": True,
            "categories": category_distribution
        }

    except Exception as e:
        calendar_logger.error(f"카테고리 분포 데이터 로딩 중 예기치 않은 오류 발생: {str(e)}")
        return {
            "success": False,
            "error_message": f"오류가 발생했습니다: {str(e)}"
        }




#### 켈린더 데이터 전처리 함수
async def process_weekly_activity_data(data: dict, user_email: str) -> dict:  # user_email 파라미터 추가
    calendar_logger.info("주간 이벤트 데이터 전처리 시작")
    
    try:
        events = data.get('events', [])
        calendar_logger.info(f"총 이벤트 수: {len(events)}")
        
        # 현재 로그인한 사용자의 일정만 필터링
        current_user_events = [
            event for event in events 
            if event.get('creator', {}).get('email') == user_email
        ]
        calendar_logger.info(f"현재 사용자의 이벤트 수: {len(current_user_events)}")
        
        # 요일별 시작/종료 시간을 저장할 딕셔너리
        daily_times = {
            0: {'start': 24, 'end': 0},  # 월요일
            1: {'start': 24, 'end': 0},  # 화요일
            2: {'start': 24, 'end': 0},  # 수요일
            3: {'start': 24, 'end': 0},  # 목요일
            4: {'start': 24, 'end': 0},  # 금요일
            5: {'start': 24, 'end': 0},  # 토요일
            6: {'start': 24, 'end': 0}   # 일요일
        }

        kst = pytz.timezone('Asia/Seoul')
        
        for event in current_user_events:
            try:
                start = event['start'].get('dateTime')
                end = event['end'].get('dateTime')
                
                if not start or not end:
                    continue
                
                # 시간 변환 및 KST 적용
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00')).astimezone(kst)
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00')).astimezone(kst)
                
                weekday = start_dt.weekday()
                start_time = start_dt.hour + start_dt.minute / 60
                end_time = end_dt.hour + end_dt.minute / 60
                
                # 해당 요일의 최소 시작 시간과 최대 종료 시간 업데이트
                daily_times[weekday]['start'] = min(daily_times[weekday]['start'], start_time)
                daily_times[weekday]['end'] = max(daily_times[weekday]['end'], end_time)
                
            except Exception as e:
                calendar_logger.error(f"이벤트 처리 중 오류 발생: {e}")
                continue
        
        # 최종 데이터 형식으로 변환
        this_week_events = [
            {
                'day': day,
                'startTime': times['start'] if times['start'] < 24 else 0,
                'endTime': times['end'] if times['end'] > 0 else 0
            }
            for day, times in daily_times.items()
            if times['start'] < 24 or times['end'] > 0  # 이벤트가 있는 날만 포함
        ]
        
        calendar_logger.info(f"최종 처리 결과: {this_week_events}")
        return {'this_week': this_week_events}
        
    except Exception as e:
        calendar_logger.error(f"데이터 전처리 중 오류 발생: {str(e)}")
        calendar_logger.error(f"상세 오류 내용: {traceback.format_exc()}")
        return {'this_week': []}

@router.get("/weekly-activity")
async def get_weekly_activity(current_user: User = Depends(get_current_user)):
    calendar_logger.info(f"사용자 {current_user.email}의 주간 활동 데이터 요청")
    try:
        raw_data = await get_weekly_activity_data(current_user.email)
        processed_data = await process_weekly_activity_data(raw_data, current_user.email)
        calendar_logger.info(f"전처리된 주간 활동 데이터: {processed_data}")  # logger를 calendar_logger로 변경
        
        return {
            "success": True,
            "data": processed_data
        }
        
    except Exception as e:
        calendar_logger.error(f"주간 활동 데이터 조회 중 오류 발생: {str(e)}")
        calendar_logger.error(f"상세 에러: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="주간 활동 데이터 조회 실패"
        )