import datetime
import math
import os
import threading  # ★時計を描きながら裏でExcelを監視するために追加したよ！
import pandas as pd
import pygame
from citam_pydraw import *

# 1. パスの設定
desktop_path = os.path.expanduser("~/Desktop")
excel_file = os.path.join(desktop_path, "homeworks.xlsx")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 📂 それぞれの時間に対応する音源ファイルを辞書型で設定
AUDIO_FILES = {
    60: os.path.join(BASE_DIR, "onsei", "bell_60.mp3"),  # 1時間前
    30: os.path.join(BASE_DIR, "onsei", "ara-m.mp3"),   # 30分前
    15: os.path.join(BASE_DIR, "onsei", "hato.mp3"),    # 15分前
    5: os.path.join(BASE_DIR, "onsei", "urusai.mp3"),   # 5分前
    0: os.path.join(BASE_DIR, "onsei", "dekita!1.mp3"), # 期限が過ぎた瞬間！
}


def init_audio():
    """音声再生の初期化"""
    pygame.mixer.init()


def play_alarm(message, minutes):
    """指定された時間（分）に応じたアラーム音を鳴らす関数"""
    print(f"⏰ {message}")

    audio_path = AUDIO_FILES.get(minutes)

    if audio_path and os.path.exists(audio_path):
        pygame.mixer.music.load(audio_path)
        pygame.mixer.music.play()
        # 5秒間待つ
        pygame.time.delay(5000)
        pygame.mixer.music.stop()
    else:
        print(f"⚠️ 音源ファイルが見つかりません。")
        print(f"   探した場所: {audio_path}")


def load_next_task_from_desktop():
    """デスクトップのhomeworks.xlsxから、現在時刻より未来（または直近1分以内）で一番締め切りが近い課題を取得する"""
    if not os.path.exists(excel_file):
        return "ファイル未検出", None, 0

    try:
        df = pd.read_excel(excel_file)
        df["締切日時"] = pd.to_datetime(df["締切日時"])

        now = datetime.datetime.now()

        # 0分前（過ぎた瞬間）の音も鳴らしたいから、締切から1分以内のデータもギリギリ取得できるように調整
        future_tasks = df[df["締切日時"] >= (now - datetime.timedelta(minutes=1))]

        if not future_tasks.empty:
            next_task_data = future_tasks.sort_values(by="締切日時").iloc[0]

            task_name = next_task_data["課題名"]
            task_deadline = next_task_data["締切日時"]

            # 同じ日の課題を数える
            closest_date = task_deadline.date()
            same_day_tasks = future_tasks[
                future_tasks["締切日時"].dt.date == closest_date
            ]
            same_day_count = len(same_day_tasks)

            return task_name, task_deadline, same_day_count
        else:
            return "未完了の課題なし", None, 0

    except Exception as e:
        print(f"⚠️ Excelの読み込み中にエラーが発生：{e}")
        return "エラー: 読み込み失敗", None, 0


# グローバル変数の初期化
task_name, deadline, same_day_count = load_next_task_from_desktop()


def alarm_monitor_loop():
    """【裏方機能】時計の描画とは別に、バックグラウンドで1秒ごとにExcelと時間を監視するループ"""
    global task_name, deadline, same_day_count
    init_audio()
    print("🚀 課題締切アラームシステムを起動 Excelを監視中...")

    alarm_minutes = [60, 30, 15, 5, 0]
    fired_alarms = set()

    while True:
        # 1秒ごとに最新の課題情報を取得
        t_name, t_deadline, count = load_next_task_from_desktop()

        # 時計の描画側でも使えるようにグローバル変数を更新
        task_name = t_name
        deadline = t_deadline
        same_day_count = count

        if deadline is not None:
            now = datetime.datetime.now()

            for minutes in alarm_minutes:
                alarm_time = deadline - datetime.timedelta(minutes=minutes)
                alarm_key = (
                    f"{task_name}_{minutes}分前_{alarm_time.strftime('%Y-%m-%d %H:%M')}"
                )

                if (
                    now.strftime("%Y-%m-%d %H:%M") == alarm_time.strftime("%Y-%m-%d %H:%M")
                    and alarm_key not in fired_alarms
                ):

                    if minutes == 0:
                        message = f"「{task_name}」の提出期限の時間になりました！"
                    else:
                        message = f"【注意】「{task_name}」の締切まであと {minutes} 分だよ！ (締切: {deadline.strftime('%H:%M')})"

                    play_alarm(message, minutes)
                    fired_alarms.add(alarm_key)

        # 1秒待つ（時計の滑らかな動きを邪魔しないように、別スレッドで待ちます）
        pygame.time.wait(1000)


@animation(True)
def draw():
    h = date.hour
    m = date.minute
    s = date.second

    # 年、月、日
    now = datetime.datetime.now()
    year = now.year
    month = now.month
    day = now.day

    print("{}:{}:{}".format(h, m, s))  # ターミナルにある時刻表示

    # 通常時の色を設定
    window_bg = color(231, 199, 146)  # 元の背景色
    dial_bg = color(255, 255, 255)  # 元の文字盤色

    # 締め切り15分前以降の判定（点滅機能）
    if deadline and task_name != "未完了の課題なし":
        deadline_dt = deadline.to_pydatetime()
        alert_time = deadline_dt - datetime.timedelta(minutes=15)

        # 15分前〜締切ぴったり（0分前）までの間、赤く点滅させるよ！
        if alert_time <= now <= deadline_dt:
            if s % 2 == 0:
                window_bg = color(255, 50, 50)  # 鮮やかな赤
                dial_bg = color(255, 200, 200)  # 薄い赤

    # 背景色の適用
    window.background(window_bg)

    # 枠
    dial = Ellipse(270, 450, 470, 470)
    dial.fill(dial_bg)  # 点滅時に文字盤色も変わるようにしたよ！
    dial.outlineFill(color(87, 58, 23))
    dial.outlineWidth(15)

    # 分針
    min_hand = Line(270, 450, 270, 285, 12)
    min_hand.fill(color(0, 0, 0)).setRotationCenter(270, 450).rotate(m * 360 / 60)
    # 分針三角形
    min_hand_tip = Triangle(265, 285, 275, 285, 270, 245)
    min_hand_tip.fill(color(0, 0, 0)).setRotationCenter(270, 450).rotate(m * 360 / 60)

    # 時針
    hou_hand = Line(270, 450, 270, 340, 28)
    hou_hand.fill(color(0, 0, 0)).setRotationCenter(270, 450).rotate(
        h * 360 / 12 + m * 360 / 12 / 60
    )

    # 時針三角形
    hou_hand_tip = Triangle(256, 340, 284, 340, 270, 290)
    hou_hand_tip.fill(color(0, 0, 0)).setRotationCenter(270, 450).rotate(
        h * 360 / 12 + m * 360 / 12 / 60
    )

    # 秒針
    sec = Line(270, 450, 270, 230, 2)
    sec.fill(color(209, 28, 44))
    sec.setRotationCenter(270, 450)
    sec.rotate(s * 360 / 60)

    # 枠の中心
    cencer = Ellipse(270, 450, 28, 28)
    cencer.fill(color(255, 255, 255))
    cencer.outlineFill(color(0, 0, 0))
    cencer.outlineWidth(5)

    # 数字
    for i in range(1, 13):
        angle = (i * 30 - 90) * math.pi / 180
        x = 270 + 180 * math.cos(angle)
        y = 450 + 180 * math.sin(angle)
        t = Text(str(i), x, y)
        t.font("Arial Rounded MT Bold", 50)

    # 目盛り
    for i in range(60):
        angle = math.radians(i * 6)
        if i % 5 == 0:
            x1 = 270 + 225 * math.sin(angle)
            y1 = 450 - 225 * math.cos(angle)
            x2 = 270 + 205 * math.sin(angle)
            y2 = 450 - 205 * math.cos(angle)
            Line(x1, y1, x2, y2, 4)
        else:
            x1 = 270 + 225 * math.sin(angle)
            y1 = 450 - 225 * math.cos(angle)
            x2 = 270 + 215 * math.sin(angle)
            y2 = 450 - 215 * math.cos(angle)
            Line(x1, y1, x2, y2, 1)

    # 画面右側に現在の対象課題名や件数を表示（上半分）
    if task_name and task_name != "未完了の課題なし":
        Rectangle(570, 50, 350, 200).fill(color(255, 255, 255))
        task_text1 = Text(f"直近の課題 (当日あと{same_day_count}件)", 750, 100)
        task_text1.font("Arial Rounded MT Bold", 24).fill(color(87, 58, 23))
        task_text2 = Text(f"{task_name}", 750, 150)
        task_text2.font("Arial Rounded MT Bold", 26).fill(color(87, 58, 23))
        task_text3 = Text(f"{deadline.strftime('%H:%M') if deadline else ''} 締切", 750, 200)
        task_text3.font("Arial Rounded MT Bold", 26).fill(color(87, 58, 23))
    else:
        # 課題がない時のハッピーな表示（上半分）
        Rectangle(570, 50, 350, 200).fill(color(255, 255, 255))
        no_task_text = Text("未完了の課題なし！✨", 750, 150)
        no_task_text.font("Arial Rounded MT Bold", 26).fill(color(34, 139, 34))

    # 画面右側に現在の対象課題名や件数を表示（下半分）
    if task_name and task_name != "未完了の課題なし":
        Rectangle(570, 300, 350, 300).fill(color(255, 255, 255))

        task_text2 = Text(f"{task_name[:5]}...　{deadline.strftime('%H:%M') if deadline else ''} 締切", 650, 350)
        task_text2.font("Arial Rounded MT Bold", 26).fill(color(87, 58, 23))

    else:
        # 課題がない時のハッピーな表示（下半分）
        Rectangle(570, 300, 350, 300).fill(color(255, 255, 255))
        no_task_text = Text("未完了の課題なし！✨", 750, 450)
        no_task_text.font("Arial Rounded MT Bold", 26).fill(color(34, 139, 34))

    # 年月日の表示
    ymd_text = Text("{}年{}月{}日".format(year, month, day), 275, 75)
    ymd_text.font("", 32)

    # デジタル時間の表示
    time_text = Text("{:02}:{:02}:{:02}".format(h, m, s), 275, 150)
    time_text.font("", 48)


if __name__ == "__main__":
    window = Window(1000, 700).title("IP_12_Clock").background(color(231, 199, 146))
    date = Date()

    # 🛠【ここがドッキングの鍵！】
    # アラーム監視（Excel読み込み）を別スレッドで動かすことで、時計が止まらずにスイスイ動くよ！
    monitor_thread = threading.Thread(target=alarm_monitor_loop, daemon=True)
    monitor_thread.start()

    draw()
    window.show()