from datetime import datetime, timedelta
import math


class Scheduler:
    def __init__(self, base_time=None):
        # Default to today at 9:00 AM
        self.base_time = base_time or datetime.now().replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        self.tasks = []
        self.blocked_times = []

    def add_task(self, task):
        """Add a task dict to be scheduled."""
        self.tasks.append(task)

    def add_goal_hybrid(self, title, total_minutes, max_block_size, priority="medium"):
        """
        Hybrid goal scheduling:
        • Fills each free interval between fixed tasks,
          capping blocks at max_block_size.
        • Any leftover time after the last fixed block
          becomes capped blocks at end-of-day.
        """
        # 1) Gather & sort today’s fixed blocks
        fixed = []
        for t in self.tasks:
            if t.get("fixed"):
                start_dt = datetime.strptime(t["start_time"], "%H:%M")
                start_dt = self.base_time.replace(
                    hour=start_dt.hour, minute=start_dt.minute
                )
                end_dt = start_dt + timedelta(minutes=t["duration"])
                fixed.append((start_dt, end_dt))
        fixed.sort(key=lambda x: x[0])

        # 2) Fill the gaps before, between, and after fixed blocks
        remaining = total_minutes
        cursor = self.base_time

        # fill gaps before & between fixed tasks
        for start_dt, end_dt in fixed:
            gap = int((start_dt - cursor).total_seconds() // 60)  # in minutes
            while remaining > 0 and gap > 0:
                block = min(max_block_size, remaining, gap)
                self.add_task({
                    "title":    title,
                    "duration": block,
                    "priority": priority,
                    "fixed":    False
                })
                remaining -= block
                gap       -= block
            cursor = max(cursor, end_dt)

        # fill any leftover time after the last fixed block
        while remaining > 0:
            block = min(max_block_size, remaining)
            self.add_task({
                "title":    title,
                "duration": block,
                "priority": priority,
                "fixed":    False
            })
            remaining -= block

    def schedule(self):
        """Return a list of tasks with start/end times, respecting fixed blocks."""
        scheduled = []
        current_time = self.base_time

        # 1) Schedule fixed tasks first
        for task in self.tasks:
            if task.get("fixed"):
                if "start_time" not in task:
                    raise ValueError(
                        f"Fixed task '{task.get('title','<unnamed>')}' is missing a start_time."
                    )
                start = datetime.strptime(task["start_time"], "%H:%M")
                start = self.base_time.replace(
                    hour=start.hour, minute=start.minute
                )
                end = start + timedelta(minutes=task["duration"])
                self.blocked_times.append((start, end))
                scheduled.append({
                    **task,
                    "start_time": start.strftime("%H:%M"),
                    "end_time":   end.strftime("%H:%M")
                })

        # 2) Then schedule flexible tasks
        for task in self.tasks:
            if task.get("fixed"):
                continue

            duration = task.get("duration", 60)
            while True:
                proposed_start = current_time
                proposed_end   = proposed_start + timedelta(minutes=duration)

                conflict = False
                for block_start, block_end in self.blocked_times:
                    if proposed_start < block_end and proposed_end > block_start:
                        current_time = block_end
                        conflict = True
                        break

                if not conflict:
                    break

            self.blocked_times.append((proposed_start, proposed_end))
            scheduled.append({
                **task,
                "start_time": proposed_start.strftime("%H:%M"),
                "end_time":   proposed_end.strftime("%H:%M")
            })
            current_time = proposed_end

        scheduled.sort(
            key=lambda t: datetime.strptime(t["start_time"], "%H:%M")
        )

        return scheduled
