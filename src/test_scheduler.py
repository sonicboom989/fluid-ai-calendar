from datetime import datetime
import os, sys
sys.path.append(os.path.dirname(__file__))
from scheduler import Scheduler


def extract(schedule, title):
    return next(item for item in schedule if item["title"] == title)


def test_move_and_remove():
    sched = Scheduler(base_time=datetime(2025, 7, 1, 9, 0))
    sched.add_task({"id": "exam", "title": "Exam", "duration": 60, "fixed": True, "start_time": "12:00"})
    sched.add_task({"id": "chores", "title": "Chores", "duration": 120, "priority": "low"})
    sched.add_task({"id": "tv", "title": "Watch TV", "duration": 60, "priority": "low"})
    sched.add_task({"id": "lunch", "title": "Lunch", "duration": 120, "priority": "low"})
    sched.add_task({
        "id": "study", "title": "Study", "duration": 180,
        "priority": "high", "earliest_time": "15:00", "latest_time": "22:00"
    })

    schedule = sched.schedule()
    assert extract(schedule, "Study")["start_time"] == "15:00"

    sched.move_task("study", earliest_time="09:00", latest_time="17:00")
    schedule = sched.schedule()
    assert extract(schedule, "Study")["start_time"] == "09:00"
    assert extract(schedule, "Lunch")["start_time"] == "16:00"

    sched.remove_task("exam")
    schedule = sched.schedule()
    assert extract(schedule, "Chores")["start_time"] == "12:00"
