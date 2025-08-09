from datetime import datetime, date, time, timedelta
from collections import defaultdict

class Scheduler:
    def __init__(self, base_time=None):
        # Defaults to today at 9:00 AM
        self.base_time = base_time or datetime.now().replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        self.tasks = []
        self.blocked_times = []

    def add_task(self, task):
        """Add a task dict and tag it with a date if missing."""
        if "date" not in task:
            task["date"] = self.base_time.date()
        self.tasks.append(task)

    def remove_task(self, task_id):
        """Remove task by id."""
        self.tasks = [t for t in self.tasks if t.get("id") != task_id]

    def move_task(self, task_id, earliest_time=None, latest_time=None):
        """Update a task's window and reschedule later."""
        for t in self.tasks:
            if t.get("id") == task_id:
                if earliest_time is not None:
                    t["earliest_time"] = earliest_time
                if latest_time is not None:
                    t["latest_time"] = latest_time
                break

    def add_goal_hybrid(self, title, total_minutes, max_block_size,
                        rest_between=0, priority="medium"):
        """
        Fill today's free gaps up to max_block_size, optionally inserting
        rest_between minutes between each goal block.
        """
        # 1) Gather & sort today's fixed blocks
        fixed = []
        for t in self.tasks:
            if t.get("fixed") and t["date"] == self.base_time.date():
                # anchor to today's base_time
                st = datetime.strptime(t["start_time"], "%H:%M")
                st = self.base_time.replace(hour=st.hour, minute=st.minute)
                en = st + timedelta(minutes=t["duration"])
                fixed.append((st, en))
        fixed.sort(key=lambda x: x[0])

        # 2) Fill gaps
        remaining = total_minutes
        cursor = self.base_time

        def emit_block(mins):
            self.add_task({
                "title":    title,
                "duration": mins,
                "priority": priority,
                "fixed":    False,
                "date":     cursor.date()
            })

        def emit_rest():
            self.add_task({
                "title":    "Rest",
                "duration": rest_between,
                "priority": "low",
                "fixed":    False,
                "date":     cursor.date()
            })

        # before & between fixed
        for st, en in fixed:
            gap = int((st - cursor).total_seconds() // 60)
            while remaining > 0 and gap > 0:
                block = min(max_block_size, remaining, gap)
                emit_block(block)
                remaining -= block
                gap       -= block
                if rest_between and remaining > 0:
                    emit_rest()
                    cursor += timedelta(minutes=rest_between)
            cursor = max(cursor, en)

        # after last fixed
        while remaining > 0:
            block = min(max_block_size, remaining)
            emit_block(block)
            remaining -= block
            if rest_between and remaining > 0:
                emit_rest()
                cursor += timedelta(minutes=rest_between)

    def add_goal_periodic(self, title, total_minutes, max_block_size,
                          start_date: date, end_date: date,
                          rest_between=0, priority="medium"):
        """
        Spread total_minutes evenly across each day in [start_date, end_date],
        using the hybrid helper each day and injecting rest_between.
        """
        # list of days
        days = []
        d = start_date
        while d <= end_date:
            days.append(d)
            d += timedelta(days=1)

        # compute daily quotas
        per_day   = total_minutes // len(days)
        remainder = total_minutes % len(days)

        for i, day in enumerate(days):
            # assign extra minute to first few days
            daily = per_day + (1 if i < remainder else 0)
            # anchor to that day at 9:00
            self.base_time     = datetime.combine(day, time(9,0))
            self.blocked_times = []
            # call hybrid for that slice
            self.add_goal_hybrid(
                title=title,
                total_minutes=daily,
                max_block_size=max_block_size,
                rest_between=rest_between,
                priority=priority
            )

    def _priority_value(self, p: str) -> int:
        return {"high": 0, "medium": 1, "low": 2}.get(p, 1)

    def _find_gap(self, dur: int, earliest: datetime, latest: datetime):
        """Find earliest available start between earliest and latest."""
        candidate = earliest
        for st, en, _ in sorted(self.blocked_times, key=lambda x: x[0]):
            if candidate + timedelta(minutes=dur) <= st:
                if candidate + timedelta(minutes=dur) <= latest:
                    return candidate
            candidate = max(candidate, en)
            if candidate > latest:
                break
        if candidate + timedelta(minutes=dur) <= latest:
            return candidate
        return None

    def _schedule_day(self, tasks_for_day):
        """Schedule tasks for a single day with windows and sliding."""
        scheduled = []
        self.blocked_times = []

        def add_block(task, start):
            dur = task.get("duration", 60)
            end = start + timedelta(minutes=dur)
            record = {**task, "start_time": start.strftime("%H:%M"),
                      "end_time": end.strftime("%H:%M")}
            self.blocked_times.append((start, end, record))
            scheduled.append(record)

        # fixed tasks
        for t in tasks_for_day:
            if t.get("fixed"):
                st = datetime.strptime(t["start_time"], "%H:%M")
                st = self.base_time.replace(hour=st.hour, minute=st.minute)
                add_block(t, st)

        # flexible tasks sorted by priority then earliest_time
        flex = [t for t in tasks_for_day if not t.get("fixed")]
        flex.sort(key=lambda x: (self._priority_value(x.get("priority", "medium")),
                                 x.get("earliest_time", "00:00")))

        def slot_task(task, allow_slide=True):
            dur = task.get("duration", 60)
            earliest = datetime.strptime(task.get("earliest_time", self.base_time.strftime("%H:%M")), "%H:%M")
            earliest = self.base_time.replace(hour=earliest.hour, minute=earliest.minute)
            latest_s = task.get("latest_time", "23:59")
            latest = datetime.strptime(latest_s, "%H:%M")
            latest = self.base_time.replace(hour=latest.hour, minute=latest.minute)
            latest -= timedelta(minutes=dur)
            start = self._find_gap(dur, earliest, latest)
            if start:
                add_block(task, start)
                return True
            if allow_slide:
                return slide_and_reschedule(task, earliest, latest)
            return False

        def slide_and_reschedule(task, earliest, latest):
            dur = task.get("duration", 60)
            removed = []
            for bt in sorted(self.blocked_times, key=lambda x: self._priority_value(x[2].get("priority", "medium")), reverse=True):
                st, en, rec = bt
                if rec.get("fixed"):
                    continue
                if self._priority_value(rec.get("priority", "medium")) <= self._priority_value(task.get("priority", "medium")):
                    continue
                self.blocked_times.remove(bt)
                scheduled.remove(rec)
                removed.append(rec)
                start = self._find_gap(dur, earliest, latest)
                if start:
                    add_block(task, start)
                    for r in removed:
                        slot_task(r, allow_slide=False)
                    return True
            for r in removed:
                slot_task(r, allow_slide=False)
            return False

        for t in flex:
            slot_task(t)

        scheduled.sort(key=lambda x: datetime.strptime(x["start_time"], "%H:%M"))
        return scheduled

    def schedule(self):
        """
        Group all tasks by their 'date', run _schedule_day on each,
        and return a combined, chronological schedule.
        """
        by_date = defaultdict(list)
        for t in self.tasks:
            by_date[t.get("date", self.base_time.date())].append(t)

        full = []
        for day in sorted(by_date):
            # reset anchor
            self.base_time = datetime.combine(day, self.base_time.timetz())
            day_sched = self._schedule_day(by_date[day])
            # tag each with date for clarity
            for item in day_sched:
                item["date"] = day.isoformat()
            full.extend(day_sched)

        # final sort by date+time
        full.sort(key=lambda x: (x["date"], x["start_time"]))
        return full
