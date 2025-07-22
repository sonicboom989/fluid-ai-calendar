from scheduler import Scheduler

sched = Scheduler()
sched.add_task({"title":"Team meeting","duration":60,"fixed":True,"start_time":"10:30"})
sched.add_goal_hybrid("Side project", total_minutes=150, max_block_size=60)


for block in sched.schedule():
    print(block)
