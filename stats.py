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
        "message_letters_count":0,
        "joined": None,
        "left": None,
        "now_in": None,
        "join_history":[],
    })

    for msg in messages:
        user = msg["user"]
        if msg["type"] == "system":
            # 입장/퇴장 처리
            action = msg["action"]
            if action == "들어왔습니다":
                if user_stats[user]["joined"] is None:
                    user_stats[user]["joined"] = msg["time"]

                user_stats[user]["left"] = None
                user_stats[user]["now_in"] = True
                # user_stats[user]["join_history"].append(msg["time"]+" " + "입장\n")
                user_stats[user]["join_history"].append(msg["time"].strftime("%Y-%m-%d %H:%M:%S") + " 입장\n")



            # elif action == "나갔습니다":
            #     if (user_stats[user]["left"] is None) or (msg["time"] > user_stats[user]["left"]):
            #         user_stats[user]["left"] = msg["time"]
            #         user_stats[user]["now_in"] = False

            elif action == "나갔습니다":
                user_stats[user]["join_history"].append(msg["time"].strftime("%Y-%m-%d %H:%M:%S") + " 퇴장\n")

                if user_stats[user]["now_in"]: # 현재 입장 상태인 경우만 처리
                    user_stats[user]["left"] = msg["time"]
                    user_stats[user]["now_in"] = False


        else:
            # 일반 메시지
            user_stats[user]["message_count"] += 1
            user_stats[user]["message_letters_count"] += len(msg["message"])

            t = msg["time"]
            if user_stats[user]["first_message_time"] is None or t < user_stats[user]["first_message_time"]:
                user_stats[user]["first_message_time"] = t
            if user_stats[user]["last_message_time"] is None or t > user_stats[user]["last_message_time"]:
                user_stats[user]["last_message_time"] = t

    return user_stats
