import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from collections import defaultdict
import re
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta
from matplotlib import rc
import numpy as np

# 외부 라이브러리: pip install tkcalendar
from tkcalendar import Calendar

# 폰트 설정 (한글 깨짐 방지)
rc('font', family='Malgun Gothic')

# 전역 변수
messages = []
user_stats = {}

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

def analyze_user_activity(messages):
    """
    주어진 messages 리스트를 바탕으로 사용자별 통계(user_stats)를 계산.
    """
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

def load_file():
    """
    파일 열기 대화상자를 통해 txt파일을 선택하고, messages / user_stats 갱신,
    테이블, 차트 갱신.
    """
    file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
    if not file_path:
        return

    with open(file_path, "r", encoding="utf-8") as f:
        chat_data = f.read()

    global messages, user_stats
    messages = parse_kakao_chat(chat_data)
    user_stats = analyze_user_activity(messages)

    apply_filter_and_sort()
    # 전체 기간 라인차트
    plot_line_chart_custom(None, None)
    # 기본 1주 파이차트
    plot_pie_chart_period("week")

def update_user_table(user_list=None):
    """
    트리뷰(user_table)에 데이터 표시.
    user_list가 주어지지 않으면, 전체 user_stats 기준.
    """
    # 기존 테이블 행 삭제
    for row in user_table.get_children():
        user_table.delete(row)

    if user_list is None:
        user_list = [(u, user_stats[u]) for u in user_stats]

    # 인덱스(#0) + (user, message_count, ...)
    for i, (user, st) in enumerate(user_list, start=1):
        j = st["joined"].strftime("%Y-%m-%d %H:%M:%S") if st["joined"] else ""
        l = st["left"].strftime("%Y-%m-%d %H:%M:%S") if st["left"] else ""
        f = st["first_message_time"].strftime("%Y-%m-%d %H:%M:%S") if st["first_message_time"] else ""
        la = st["last_message_time"].strftime("%Y-%m-%d %H:%M:%S") if st["last_message_time"] else ""

        user_table.insert(
            "",
            "end",
            text=str(i),  # 인덱스
            values=(user, st["message_count"], f, la, j, l)
        )

def show_user_details(event):
    """
    유저 테이블 더블 클릭 -> 해당 유저의 상세정보 창
    (왼쪽: 해당 유저 라인차트, 오른쪽: 대화내용)
    """
    selected_item = user_table.selection()
    if not selected_item:
        return

    user = user_table.item(selected_item)["values"][0]
    user_messages = [m for m in messages if (m["type"] == "message" and m["user"] == user)]

    details_win = tk.Toplevel(root)
    details_win.title(f"{user}의 대화 내용")

    # 좌/우 레이아웃
    left_frame = tk.Frame(details_win)
    left_frame.pack(side="left", fill="both", expand=False)

    right_frame = tk.Frame(details_win)
    right_frame.pack(side="left", fill="both", expand=True)

    # (1) 왼쪽 라인차트
    plot_user_line_chart(user, left_frame)

    # (2) 오른쪽 텍스트
    scroll = tk.Scrollbar(right_frame, orient="vertical")
    scroll.pack(side="right", fill="y")

    text_widget = tk.Text(right_frame, wrap="word", width=80, height=20, font=("Arial", 10), yscrollcommand=scroll.set)
    text_widget.pack(side="left", fill="both", expand=True)
    scroll.config(command=text_widget.yview)

    for msg in user_messages:
        t_str = msg["time"].strftime("%Y-%m-%d %H:%M:%S")
        text_widget.insert("end", f"[{t_str}] {msg['message']}\n")

def apply_filter_and_sort():
    """
    검색(유저명) + 정렬
    """
    keyword = search_var.get().strip().lower()
    sort_col = sort_col_var.get()
    direction = sort_dir_var.get()
    reverse_sort = (direction == "내림차순")

    filtered = []
    for u, st in user_stats.items():
        if keyword in u.lower():
            filtered.append((u, st))

    def sort_key(item):
        user, stats = item
        if sort_col == "user":
            return user.lower()
        elif sort_col == "message_count":
            return stats["message_count"]
        elif sort_col == "first_message_time":
            return stats["first_message_time"] or datetime.min
        elif sort_col == "last_message_time":
            return stats["last_message_time"] or datetime.min
        elif sort_col == "joined_time":
            return stats["joined"] or datetime.min
        elif sort_col == "left_time":
            return stats["left"] or datetime.min
        else:
            return user.lower()

    filtered.sort(key=sort_key, reverse=reverse_sort)
    update_user_table(filtered)

def plot_pie_chart_period(period):
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

    plot_pie_chart_custom(start_time, datetime.now())

def plot_pie_chart_custom(start_dt, end_dt):
    """
    start_dt~end_dt 메시지만으로 파이차트 + Top20
    """
    for w in left_subframe.winfo_children():
        w.destroy()
    for w in middle_subframe.winfo_children():
        w.destroy()

    # 메시지 필터
    filtered_msgs = [m for m in messages if m["type"] == "message"]
    if start_dt and end_dt:
        filtered_msgs = [m for m in filtered_msgs if (m["time"] >= start_dt and m["time"] <= end_dt)]

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

    # 파스텔 계열 색상
    # top_20 최대 길이가 21이므로 그에 맞춰 색상 수 지정
    cmap = plt.get_cmap('Pastel2')  
    colors = [cmap(i / (len(top_20))) for i in range(len(top_20))]

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.pie(counts, 
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

def open_custom_pie_calendar():
    """
    파이차트 기간 커스텀 (Calendar 2개)
    """
    cal_win = tk.Toplevel(root)
    cal_win.title("점유율 차트 기간 선택")

    tk.Label(cal_win, text="Start Date").pack(pady=5)
    cal1 = Calendar(cal_win, selectmode='day', date_pattern='yyyy-mm-dd')
    cal1.pack(pady=5)

    tk.Label(cal_win, text="End Date").pack(pady=5)
    cal2 = Calendar(cal_win, selectmode='day', date_pattern='yyyy-mm-dd')
    cal2.pack(pady=5)

    def on_ok():
        s_date = datetime.strptime(cal1.get_date(), "%Y-%m-%d")
        e_date = datetime.strptime(cal2.get_date(), "%Y-%m-%d")
        if s_date > e_date:
            messagebox.showerror("Error", "시작일이 종료일보다 늦습니다.")
            return

        plot_pie_chart_custom(s_date, e_date + timedelta(hours=23, minutes=59, seconds=59))
        cal_win.destroy()

    btn_ok = tk.Button(cal_win, text="확인", command=on_ok)
    btn_ok.pack(pady=10)

def open_custom_line_calendar():
    """
    라인차트 기간 커스텀 (Calendar 2개)
    """
    cal_win = tk.Toplevel(root)
    cal_win.title("대화량 차트 기간 선택")

    tk.Label(cal_win, text="Start Date").pack(pady=5)
    cal1 = Calendar(cal_win, selectmode='day', date_pattern='yyyy-mm-dd')
    cal1.pack(pady=5)

    tk.Label(cal_win, text="End Date").pack(pady=5)
    cal2 = Calendar(cal_win, selectmode='day', date_pattern='yyyy-mm-dd')
    cal2.pack(pady=5)

    def on_ok():
        s_date = datetime.strptime(cal1.get_date(), "%Y-%m-%d")
        e_date = datetime.strptime(cal2.get_date(), "%Y-%m-%d")
        if s_date > e_date:
            messagebox.showerror("Error", "시작일이 종료일보다 늦습니다.")
            return

        plot_line_chart_custom(s_date, e_date + timedelta(hours=23, minutes=59, seconds=59))
        cal_win.destroy()

    btn_ok = tk.Button(cal_win, text="확인", command=on_ok)
    btn_ok.pack(pady=10)

def plot_line_chart_custom(start_dt, end_dt):
    """
    메인화면 오른쪽 라인차트 (전체 or 사용자 지정 기간)
    """
    for w in right_subframe.winfo_children():
        w.destroy()

    filtered = [m for m in messages if m["type"] == "message"]
    if start_dt and end_dt:
        filtered = [m for m in filtered if (m["time"] >= start_dt and m["time"] <= end_dt)]

    if not filtered:
        tk.Label(right_subframe, text="No messages for line chart").pack()
        return

    day_counter = defaultdict(int)
    for msg in filtered:
        d_str = msg["time"].strftime("%Y-%m-%d")
        day_counter[d_str] += 1

    sorted_days = sorted(day_counter.keys())
    day_counts = [day_counter[d] for d in sorted_days]

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

def plot_user_line_chart(user, parent_frame):
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


# ----------------------------------
# GUI 설정
# ----------------------------------
root = tk.Tk()
root.title("카카오톡 대화 분석 프로그램")

# 상단 버튼들
button_frame = tk.Frame(root)
button_frame.pack(pady=5, fill="x")

load_btn = tk.Button(button_frame, text="파일 열기", command=load_file, font=("Arial", 12))
load_btn.pack(side="left", padx=5)

day_button = tk.Button(button_frame, text="파이차트(1일)", command=lambda: plot_pie_chart_period("day"))
day_button.pack(side="left", padx=5)

week_button = tk.Button(button_frame, text="파이차트(1주일)", command=lambda: plot_pie_chart_period("week"))
week_button.pack(side="left", padx=5)

month_button = tk.Button(button_frame, text="파이차트(1개월)", command=lambda: plot_pie_chart_period("month"))
month_button.pack(side="left", padx=5)

# 파이차트 전체 기간 버튼
btn_pie_full = tk.Button(button_frame, text="파이차트(전체)", command=lambda: plot_pie_chart_custom(None, None))
btn_pie_full.pack(side="left", padx=5)

btn_pie_custom = tk.Button(button_frame, text="Custom Range(점유율 차트)", command=open_custom_pie_calendar, font=("Arial", 10))
btn_pie_custom.pack(side="left", padx=5)

# 라인차트 전체 기간 버튼
btn_line_full = tk.Button(button_frame, text="대화량 차트(전체)", command=lambda: plot_line_chart_custom(None, None))
btn_line_full.pack(side="left", padx=5)

btn_line_custom = tk.Button(button_frame, text="Custom Range(대화량 차트)", command=open_custom_line_calendar, font=("Arial", 10))
btn_line_custom.pack(side="left", padx=5)

# 차트 영역 (상단)
top_frame = tk.Frame(root)
top_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)

left_subframe = tk.Frame(top_frame)
left_subframe.pack(side="left", fill="both", expand=True)

middle_subframe = tk.Frame(top_frame)
middle_subframe.pack(side="left", fill="both", expand=False, padx=10)

right_subframe = tk.Frame(top_frame)
right_subframe.pack(side="left", fill="both", expand=True, padx=10)

# 검색 / 정렬
filter_frame = tk.Frame(root)
filter_frame.pack(pady=5, fill="x")

search_label = tk.Label(filter_frame, text="검색(유저명):", font=("Arial", 10))
search_label.pack(side="left", padx=5)

search_var = tk.StringVar()
search_entry = tk.Entry(filter_frame, textvariable=search_var, font=("Arial", 10), width=20)
search_entry.pack(side="left")

search_button = tk.Button(filter_frame, text="검색", command=apply_filter_and_sort, font=("Arial", 10))
search_button.pack(side="left", padx=5)

sort_label = tk.Label(filter_frame, text="정렬 기준:", font=("Arial", 10))
sort_label.pack(side="left", padx=5)

sort_col_var = tk.StringVar()
sort_col_combobox = ttk.Combobox(
    filter_frame,
    textvariable=sort_col_var,
    values=["user", "message_count", "first_message_time", "last_message_time", "joined_time", "left_time"],
    state="readonly",
    width=18
)
sort_col_combobox.current(1)
sort_col_combobox.pack(side="left")

sort_dir_var = tk.StringVar()
sort_dir_combobox = ttk.Combobox(
    filter_frame,
    textvariable=sort_dir_var,
    values=["오름차순", "내림차순"],
    state="readonly",
    width=8
)
sort_dir_combobox.current(1)
sort_dir_combobox.pack(side="left", padx=5)

sort_btn = tk.Button(filter_frame, text="정렬 적용", command=apply_filter_and_sort, font=("Arial", 10))
sort_btn.pack(side="left", padx=5)

# 하단 테이블
bottom_frame = tk.Frame(root)
bottom_frame.pack(side="bottom", fill="both", expand=True, padx=10, pady=10)

scroll = tk.Scrollbar(bottom_frame, orient="vertical")
scroll.pack(side="right", fill="y")

columns = ("user", "message_count", "first_message_time", "last_message_time", "joined_time", "left_time")
user_table = ttk.Treeview(bottom_frame, columns=columns, height=15, show="headings", yscrollcommand=scroll.set)

# (1) 인덱스(#0) 컬럼 활성화
user_table["show"] = ("tree","headings")
user_table.heading("#0", text="No.")   # 인덱스 컬럼

user_table.heading("user", text="User")
user_table.heading("message_count", text="Message Count")
user_table.heading("first_message_time", text="First Msg Time")
user_table.heading("last_message_time", text="Last Msg Time")
user_table.heading("joined_time", text="Joined")
user_table.heading("left_time", text="Left")

user_table.pack(side="left", fill="both", expand=True)
scroll.config(command=user_table.yview)

# 테이블 더블클릭 -> 상세정보
user_table.bind("<Double-1>", show_user_details)

root.mainloop()
