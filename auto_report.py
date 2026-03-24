#!/usr/bin/env python3
"""自动化简报脚本

1. 使用 schedule 设定每天 09:00 自动运行天气和招投标爬虫
2. 成功后自动执行 git add . / git commit / git push
"""

import subprocess
import sys
import time
from datetime import datetime

import schedule

from weather_reporter import WeatherReporter
from tender_reporter import TenderReporter


def generate_weather_report():
    reporter = WeatherReporter()
    print("[1/2] 生成南京气象简报...")

    weather_data = reporter.get_weather_data()
    markdown_report = reporter.generate_markdown_report(weather_data)
    filename = reporter.save_report(markdown_report)

    print(f"[1/2] 气象简报已保存：{filename}")
    return filename


def generate_tender_report():
    reporter = TenderReporter()
    print("[2/2] 生成光伏招投标简报...")

    tenders = reporter.get_tender_data(max_pages=3)
    markdown_report = reporter.generate_markdown_report(tenders)
    filename = reporter.save_report(markdown_report)

    print(f"[2/2] 招投标简报已保存：{filename}")
    return filename


def git_commit_and_push():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"自动更新简报：{timestamp}"

    print("[3/3] 执行 Git 操作：add / commit / push...")
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", message], check=True)
        subprocess.run(["git", "push", "origin", "master"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Git 操作失败：{e}")
        return False

    print("✅ Git 推送完成")
    return True


def run_report_pipeline():
    print("=== 自动报告执行开始 ===")
    success = True

    try:
        generate_weather_report()
    except Exception as e:
        print(f"❌ 气象报告失败：{e}")
        success = False

    try:
        generate_tender_report()
    except Exception as e:
        print(f"❌ 招投标报告失败：{e}")
        success = False

    if success:
        git_success = git_commit_and_push()
        if not git_success:
            print("⚠️ Git 提交/推送失败，请检查本地仓库状态和网络。")
    else:
        print("⚠️ 存在一个或多个报告生成失败，已跳过 Git 提交。")

    print("=== 自动报告执行结束 ===\n")


def schedule_daily():
    schedule.every().day.at("09:00").do(run_report_pipeline)
    print("已设置每天 09:00 自动运行报告任务")

    # 立即执行一次作为启动验证
    run_report_pipeline()

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    # 可通过命令行参数 --once 只执行一次并退出，用于测试
    if "--once" in sys.argv:
        run_report_pipeline()
        sys.exit(0)

    schedule_daily()
