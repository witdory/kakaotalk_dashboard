# stats.py
from collections import defaultdict

def analyze_user_activity(messages):
    """
    주어진 messages 리스트를 바탕으로 사용자별 통계(user_stats)를 계산.
    """
    from datetime import datetime  # 함수 안에서만 쓰이므로 내부 import

    user_stats = defaultdict(lambda: {
        "message_count": 0,
        "first_message_time": None,
        "last_message_time": None,
        "joined": None,
        "left": None,
    })

    for msg in messages:
        user = msg["user"]
        if msg["type"] == "system":
            # 입장/퇴장 처리
            action = msg["action"]
            if action == "들어왔습니다":
                if user_stats[user]["joined"] is None:
                    user_stats[user]["joined"] = msg["time"]
            elif action == "나갔습니다":
                if (user_stats[user]["left"] is None) or (msg["time"] > user_stats[user]["left"]):
                    user_stats[user]["left"] = msg["time"]
        else:
            # 일반 메시지
            user_stats[user]["message_count"] += 1
            t = msg["time"]
            if user_stats[user]["first_message_time"] is None or t < user_stats[user]["first_message_time"]:
                user_stats[user]["first_message_time"] = t
            if user_stats[user]["last_message_time"] is None or t > user_stats[user]["last_message_time"]:
                user_stats[user]["last_message_time"] = t

    return user_stats
