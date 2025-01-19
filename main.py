# main.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timedelta
from tkcalendar import Calendar

# 우리가 분할해놓은 파일에서 함수/클래스 import
from parse_kakao import parse_kakao_chat
from stats import analyze_user_activity
from charts import (
    plot_pie_chart_period,
    plot_pie_chart_custom,
    plot_line_chart_custom,
    plot_user_line_chart
)
import matplotlib.pyplot as plt
from matplotlib import rcParams

# 한글 폰트 설정
rcParams['font.family'] = 'Malgun Gothic'  # Windows의 맑은 고딕 폰트
rcParams['axes.unicode_minus'] = False    # 마이너스 기호 깨짐 방지

# 전역 리스트/딕셔너리
messages = []
user_stats = {}

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
    plot_line_chart_custom(messages, right_subframe, None, None)
    # 기본 1주 파이차트
    plot_pie_chart_period(messages, left_subframe, middle_subframe, "week")

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
        j = st["joined"].strftime("%Y-%m-%d") if st["joined"] else ""
        l = st["left"].strftime("%Y-%m-%d") if st["left"] else ""
        f = st["first_message_time"].strftime("%Y-%m-%d %H:%M:%S") if st["first_message_time"] else ""
        la = st["last_message_time"].strftime("%Y-%m-%d %H:%M:%S") if st["last_message_time"] else ""
        mlc = st["message_letters_count"]  # 문자 수 가져오기
        user_table.insert(
            "",
            "end",
            text=str(i),  # 인덱스
            values=(user, st["message_count"], mlc, f, la, j, l)
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
    
    left_upper_frame = tk.Frame(left_frame)
    left_upper_frame.pack(side="top", fill="both")

    left_lower_frame = tk.Frame(left_frame)
    left_lower_frame.pack(side="top", fill="both")


    right_frame = tk.Frame(details_win)
    right_frame.pack(side="left", fill="both", expand=True)

    # (1) 왼쪽 라인차트 (개별 유저용)
    plot_user_line_chart(messages, user, left_upper_frame)

    #왼쪽 차트 하단 텍스트
    join_history_text = tk.Text(left_lower_frame, wrap="word")
    join_history_text.pack(fill="both", expand=True, padx=10, pady=10)

     # 사용자 입장/퇴장 기록 작성
    user_stats_entry = user_stats.get(user, {})
    join_time = user_stats_entry.get("joined")
    leave_time = user_stats_entry.get("left")


    history_text = f"사용자: {user}\n"
    # history_text += f"입장 시간: {join_time.strftime('%Y-%m-%d %H:%M:%S') if join_time else '정보 없음'}\n"
    # history_text += f"퇴장 시간: {leave_time.strftime('%Y-%m-%d %H:%M:%S') if leave_time else '정보 없음'}\n"
    # history_text += f"현재 방 상태: {'현재 방에 있음' if user_stats_entry.get('now_in') else '퇴장함'}\n"
    # history_text += "".join(user_stats_entry["join_history"])
    history_text += "".join(user_stats_entry.get("join_history", []))
    print(history_text)
    join_history_text.insert("1.0", history_text)
    join_history_text.config(state="disabled")  # 수정 불가로 설정

    # (2) 오른쪽 텍스트
    scroll = tk.Scrollbar(right_frame, orient="vertical")
    scroll.pack(side="right", fill="y")

    text_widget = tk.Text(right_frame, wrap="word", width=80, height=20, font=("Arial", 10), yscrollcommand=scroll.set)
    text_widget.pack(side="left", fill="both", expand=True)
    scroll.config(command=text_widget.yview)

    for msg in user_messages:
        t_str = msg["time"].strftime("%Y-%m-%d %H:%M:%S")
        text_widget.insert("end", f"[{t_str}] {msg['message']}\n")
    text_widget.config(state="disabled")# 수정 불가로 설정
    

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

        plot_pie_chart_custom(messages, left_subframe, middle_subframe, s_date, e_date + timedelta(hours=23, minutes=59, seconds=59))
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

        plot_line_chart_custom(messages, right_subframe, s_date, e_date + timedelta(hours=23, minutes=59, seconds=59))
        cal_win.destroy()

    btn_ok = tk.Button(cal_win, text="확인", command=on_ok)
    btn_ok.pack(pady=10)


# -----------------------
# 아래부터 GUI 설정
# -----------------------
root = tk.Tk()
root.title("카카오톡 이용자 분석 프로그램")

# 상단 버튼들
button_frame = tk.Frame(root)
button_frame.pack(pady=5, fill="x")

load_btn = tk.Button(button_frame, text="파일 열기", command=load_file, font=("Arial", 12))
load_btn.pack(side="left", padx=5)

day_button = tk.Button(button_frame, text="대화 점유율(1일)", 
                       command=lambda: plot_pie_chart_period(messages, left_subframe, middle_subframe, "day"))
day_button.pack(side="left", padx=5)

week_button = tk.Button(button_frame, text="대화 점유율(1주일)", 
                        command=lambda: plot_pie_chart_period(messages, left_subframe, middle_subframe, "week"))
week_button.pack(side="left", padx=5)

month_button = tk.Button(button_frame, text="대화 점유율(1개월)", 
                         command=lambda: plot_pie_chart_period(messages, left_subframe, middle_subframe, "month"))
month_button.pack(side="left", padx=5)

# 파이차트 전체 기간 버튼
btn_pie_full = tk.Button(button_frame, text="대화 점유율(전체)", 
                         command=lambda: plot_pie_chart_custom(messages, left_subframe, middle_subframe, None, None))
btn_pie_full.pack(side="left", padx=5)

btn_pie_custom = tk.Button(button_frame, text="Custom Range(대화 점유율)", 
                           command=open_custom_pie_calendar, font=("Arial", 10))
btn_pie_custom.pack(side="left", padx=5)

# 라인차트 전체 기간 버튼
btn_line_full = tk.Button(button_frame, text="대화량 차트(전체)",
                          command=lambda: plot_line_chart_custom(messages, right_subframe, None, None))
btn_line_full.pack(side="left", padx=5)

btn_line_custom = tk.Button(button_frame, text="Custom Range(대화량 차트)", 
                            command=open_custom_line_calendar, font=("Arial", 10))
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

columns = ("user", "message_count", "message_letters_count", "first_message_time", "last_message_time", "joined_time", "left_time")
user_table = ttk.Treeview(bottom_frame, columns=columns, height=15, show="headings", yscrollcommand=scroll.set)

# (1) 인덱스(#0) 컬럼 활성화
user_table["show"] = ("tree","headings")
user_table.column("#0", width=50, minwidth=30, anchor="center")  # 인덱스 컬럼 폭 조정
user_table.heading("#0", text="No.")   # 인덱스 컬럼

user_table.heading("user", text="User")
user_table.heading("message_count", text="Message Count")
user_table.column("message_count", width=120, anchor="center")

user_table.heading("message_letters_count", text="Message Letters Count")
user_table.column("message_letters_count", width=150, anchor="center")

user_table.heading("first_message_time", text="First Msg Time")
user_table.column("first_message_time", width=180, anchor="center")

user_table.heading("last_message_time", text="Last Msg Time")
user_table.column("last_message_time", width=180, anchor="center")

user_table.heading("joined_time", text="Joined")
user_table.column("joined_time", width=120, anchor="center")

user_table.heading("left_time", text="Left")
user_table.column("left_time", width=120, anchor="center")

user_table.pack(side="left", fill="both", expand=True)
scroll.config(command=user_table.yview)

# 테이블 더블클릭 -> 상세정보
user_table.bind("<Double-1>", show_user_details)

root.mainloop()
