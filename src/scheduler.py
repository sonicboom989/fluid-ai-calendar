from datetime import datetime, date, time, timedelta
from collections import defaultdict
import math

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

    def _schedule_day(self, tasks_for_day):
        """
        Schedule one day's tasks (fixed + flexible) returning a list of
        dicts with start_time/end_time on that date.
        """
        scheduled = []
        self.blocked_times = []
        current_time = self.base_time

        # fixed first
        for t in tasks_for_day:
            if t.get("fixed"):
                st = datetime.strptime(t["start_time"], "%H:%M")
                st = current_time.replace(hour=st.hour, minute=st.minute)
                en = st + timedelta(minutes=t["duration"])
                self.blocked_times.append((st, en))
                scheduled.append({
                    **t,
                    "start_time": st.strftime("%H:%M"),
                    "end_time":   en.strftime("%H:%M")
                })

        # flexible next
        for t in tasks_for_day:
            if t.get("fixed"):
                continue
            dur = t.get("duration", 60)
            while True:
                pst = current_time
                pen = pst + timedelta(minutes=dur)
                conflict = False
                for bs, be in self.blocked_times:
                    if pst < be and pen > bs:
                        current_time = be
                        conflict = True
                        break
                if not conflict:
                    break
            self.blocked_times.append((pst, pen))
            scheduled.append({
                **t,
                "start_time": pst.strftime("%H:%M"),
                "end_time":   pen.strftime("%H:%M")
            })
            current_time = pen

        # sort by time and return
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
