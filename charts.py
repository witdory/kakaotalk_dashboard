# charts.py
import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import defaultdict
from datetime import datetime, timedelta
import numpy as np

# 파이차트 (기간별 호출) -> 내부적으로 plot_pie_chart_custom 호출
def plot_pie_chart_period(messages, left_subframe, middle_subframe, period):
    """
    1일 / 1주 / 1개월 간 메시지 기준 파이차트
    """
    if period == "day":
        start_time = datetime.now() - timedelta(days=1)
    elif period == "week":
        start_time = datetime.now() - timedelta(weeks=1)
    elif period == "month":
        start_time = datetime.now() - timedelta(days=30)
    else:
        start_time = datetime.now() - timedelta(weeks=1)

    plot_pie_chart_custom(messages, left_subframe, middle_subframe, start_time, datetime.now())

def plot_pie_chart_custom(messages, left_subframe, middle_subframe, start_dt, end_dt):
    """
    start_dt~end_dt 메시지만으로 파이차트 + Top20
    """
    # 기존 위젯 삭제
    for w in left_subframe.winfo_children():
        w.destroy()
    for w in middle_subframe.winfo_children():
        w.destroy()

    # 메시지 필터
    filtered_msgs = [m for m in messages if m["type"] == "message"]
    if start_dt and end_dt:
        filtered_msgs = [m for m in filtered_msgs if (start_dt <= m["time"] <= end_dt)]

    from collections import defaultdict
    user_count = defaultdict(int)
    for msg in filtered_msgs:
        user_count[msg["user"]] += 1

    if not user_count:
        tk.Label(left_subframe, text="No messages in this range").pack()
        tk.Label(middle_subframe, text="No data").pack()
        return

    sorted_list = sorted(user_count.items(), key=lambda x: x[1], reverse=True)
    top_20 = sorted_list[:20]
    others = sorted_list[20:]
    if others:
        sum_others = sum(cnt for _, cnt in others)
        top_20.append(("기타", sum_others))

    users = [t[0] for t in top_20]
    counts = [t[1] for t in top_20]

    # 파스텔 계열 색상 (Pastel2)
    cmap = plt.get_cmap('Pastel2')
    colors = [cmap(i / len(top_20)) for i in range(len(top_20))]

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.pie(
        counts, 
        labels=users, 
        autopct='%1.1f%%', 
        startangle=90,
        colors=colors,
        textprops={'fontsize': 8}  # 라벨 폰트 사이즈 작게
    )
    if start_dt and end_dt:
        ax.set_title(f"점유율 차트 ({start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')})")
    else:
        ax.set_title("점유율 차트 (전체 기간)")

    canvas = FigureCanvasTkAgg(fig, master=left_subframe)
    canvas.draw()
    canvas.get_tk_widget().pack()

    label_top20 = tk.Label(middle_subframe, text="Top 20 Users", font=("Arial", 10, "bold"))
    label_top20.pack(pady=5)

    text_top20 = tk.Text(middle_subframe, width=25, height=22, font=("Arial", 10))
    text_top20.pack()
    for i, (u, c) in enumerate(top_20, start=1):
        text_top20.insert("end", f"{i}) {u}: {c}\n")
    text_top20.config(state="disabled")


def plot_line_chart_custom(messages, right_subframe, start_dt, end_dt):
    """
    메인화면 오른쪽 라인차트 (전체 or 사용자 지정 기간)
    """
    for w in right_subframe.winfo_children():
        w.destroy()

    filtered = [m for m in messages if m["type"] == "message"]
    if start_dt and end_dt:
        filtered = [m for m in filtered if start_dt <= m["time"] <= end_dt]

    if not filtered:
        tk.Label(right_subframe, text="No messages for line chart").pack()
        return

    day_counter = defaultdict(int)
    for msg in filtered:
        d_str = msg["time"].strftime("%Y-%m-%d")
        day_counter[d_str] += 1

    sorted_days = sorted(day_counter.keys())
    day_counts = [day_counter[d] for d in sorted_days]

    # 30일 이동평균
    def moving_average(values, window=30):
        ma_vals = []
        for i in range(len(values)):
            start_idx = max(0, i - window + 1)
            subarr = values[start_idx : i+1]
            ma_vals.append(sum(subarr)/len(subarr))
        return ma_vals

    ma_vals = moving_average(day_counts, 30)

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(sorted_days, day_counts, color='blue', marker='', label='Daily Count')
    ax.plot(sorted_days, ma_vals, color='red', marker='', linestyle='--', label='30-day MA')

    n = len(sorted_days)
    if n > 10:
        step = n // 10
        xticks = []
        xtick_labels = []
        for i, day in enumerate(sorted_days):
            if i % step == 0 or i == n-1:
                xticks.append(i)
                xtick_labels.append(day)
        ax.set_xticks(xticks)
        ax.set_xticklabels(xtick_labels, rotation=45, ha='right')
    else:
        plt.xticks(rotation=45, ha='right')

    if start_dt and end_dt:
        title_str = f"대화량 추이 ({start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')})"
    else:
        title_str = "대화량 추이(전체)"
    ax.set_title(title_str)
    ax.set_xlabel("Date")
    ax.set_ylabel("Messages")
    ax.legend()
    plt.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=right_subframe)
    canvas.draw()
    canvas.get_tk_widget().pack()


def plot_user_line_chart(messages, user, parent_frame):
    """
    상세정보 창에서, 선택된 user만의 일자별 대화량 + 이동평균 라인차트를 표시
    """
    user_msgs = [m for m in messages if m["type"] == "message" and m["user"] == user]
    if not user_msgs:
        tk.Label(parent_frame, text="No messages for this user chart").pack()
        return

    day_counter = defaultdict(int)
    for msg in user_msgs:
        d_str = msg["time"].strftime("%Y-%m-%d")
        day_counter[d_str] += 1

    sorted_days = sorted(day_counter.keys())
    day_counts = [day_counter[d] for d in sorted_days]

    # 7일 이동평균
    def moving_average(values, window=7):
        ma_vals = []
        for i in range(len(values)):
            start_idx = max(0, i - window + 1)
            subarr = values[start_idx : i+1]
            ma_vals.append(sum(subarr)/len(subarr))
        return ma_vals

    ma_vals = moving_average(day_counts, 7)

    fig, ax = plt.subplots(figsize=(4, 3))
    ax.plot(sorted_days, day_counts, color='blue', marker='', label='User Daily')
    ax.plot(sorted_days, ma_vals, color='red', marker='', linestyle='--', label='7-day MA')

    n = len(sorted_days)
    if n > 6:
        step = max(1, n // 6)
        xticks = []
        xtick_labels = []
        for i, day in enumerate(sorted_days):
            if i % step == 0 or i == n-1:
                xticks.append(i)
                xtick_labels.append(day)
        ax.set_xticks(xticks)
        ax.set_xticklabels(xtick_labels, rotation=45, ha='right')
    else:
        plt.xticks(rotation=45, ha='right')

    ax.set_title(f"{user}의 대화량 추이")
    ax.set_xlabel("Date")
    ax.set_ylabel("Messages")
    ax.legend()
    plt.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=parent_frame)
    canvas.draw()
    canvas.get_tk_widget().pack()
