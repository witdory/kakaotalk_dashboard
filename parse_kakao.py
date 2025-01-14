# parse_kakao.py
import re
from datetime import datetime

def parse_kakao_chat(chat_data):
    """
    카카오톡 txt 파일을 파싱하여 messages 리스트를 반환.
    """
    messages = []
    date_pattern = r"^-+\s+(\d{4})년\s+(\d{1,2})월\s+(\d{1,2})일\s+[가-힣]+\s+-+$"
    message_pattern = r"\[(.*?)\] \[(.*?)\] (.+)"
    join_leave_pattern = r"(.*?)님이 (들어왔습니다|나갔습니다)\."

    current_date = None

    def parse_kakao_time(time_str):
        """
        '오전 9:00' / '오후 10:22' 등을 24시간제로 변환
        """
        period, clock = time_str.split()
        hour, minute = map(int, clock.split(":"))
        if period == "오후" and hour != 12:
            hour += 12
        if period == "오전" and hour == 12:
            hour = 0
        return hour, minute

    for line in chat_data.split("\n"):
        line_stripped = line.strip()

        # 날짜 라인
        date_match = re.match(date_pattern, line_stripped)
        if date_match:
            year, month, day = map(int, date_match.groups())
            current_date = datetime(year, month, day)
            continue

        # 입장/퇴장 (system)
        join_leave_match = re.match(join_leave_pattern, line_stripped)
        if join_leave_match:
            user, action = join_leave_match.groups()
            if not current_date:
                current_date = datetime.now()
            messages.append({
                "type": "system",
                "user": user,
                "action": action,
                "time": current_date
            })
            continue

        # 일반 메시지
        message_match = re.match(message_pattern, line_stripped)
        if message_match:
            if not current_date:
                current_date = datetime.now()

            name, time_str, msg_text = message_match.groups()
            try:
                h, m = parse_kakao_time(time_str)
                msg_time = datetime(
                    current_date.year,
                    current_date.month,
                    current_date.day,
                    h, m, 0, 0
                )
                messages.append({
                    "type": "message",
                    "user": name,
                    "time": msg_time,
                    "message": msg_text
                })
            except ValueError:
                print(f"[WARNING] Invalid time format: {time_str}")

    return messages
