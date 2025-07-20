from flask import Flask, request, jsonify
import uuid

app = Flask(__name__)

tasks = []

@app.route('/')
def home():
    return "AI Calendar Backend is running!"

@app.route('/add-task', methods=["POST"])
def add_task():
    data = request.get_json()

    #Extract Basic Fields
    task = {
        "id": str(uuid.uuid4()),  # Generate a unique ID for the task
        "title:": data.get("title"),
        "duration": data.get("duration"),
        "priority": data.get("priority", "medium"),
        "fixed": data.get("fixed", False),
    }

    tasks.append(task)
    print(f"Added task:{task}")
    return jsonify({"status": "success","task": task}), 201

@app.route('/get-tasks', methods=["GET"])
def get_tasks():
    return jsonify({"tasks": tasks}), 200

from datetime import datetime, timedelta

@app.route("/schedule",methods=["POST"])
def schedule_tasks():
    current_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

    scheduled = []
    blocked_times = []
    for task in tasks:
        if task.get("fixed"):
            if "start_time" not in task:
                task_title = task.get("title", "<unnamed task>")
                if "start_time" not in task:
                    return jsonify({"error": f"Fixed task '{task_title}' is missing a start_time."}), 400

            
            start = datetime.strptime(task["start_time"], "%H:%M")
            end = start + timedelta(minutes=task["duration"])
            blocked_times.append((start, end))
            scheduled.append({
                **task,
                "start_time": task["start_time"],
                "end_time": end.strftime("%H:%M")
            })
    for task in tasks:
        if task.get("fixed"):
            continue

        #Assign Start and end times
        duration = task.get("duration", 60) # Default to 60 minutes if not specified
        while True:
            overlap = False
            for block_start, block_end in blocked_times:
                proposed_end = current_time + timedelta(minutes=duration)
                if current_time < block_end and proposed_end > block_start:
                    overlap = True
                    current_time = block_end
                    break
            if not overlap:
                break
   
        end_time = current_time + timedelta(minutes=duration)
        blocked_times.append((current_time, end_time))


        scheduled_task = {
            **task,
            "start_time": start_time.strftime("%H:%M"),
            "end_time": end_time.strftime("%H:%M")

        }
        scheduled.append(scheduled_task)

        current_time = end_time
    return jsonify({"scheduled" : scheduled}), 200

@app.route("/reset-tasks", methods=["POST"])
def reset_tasks():
    tasks.clear()
    return jsonify({"status": "cleared"}), 200

if __name__ == '__main__':
    app.run(debug=True)