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
        "title": data.get("title"),
        "duration": data.get("duration"),
        "priority": data.get("priority", "medium"),
        "fixed": data.get("fixed", False),
    }

    if "start_time" in data:
        task["start_time"] = data["start_time"]

    tasks.append(task)
    print(f"Added task:{task}")
    return jsonify({"status": "success","task": task}), 201

@app.route('/get-tasks', methods=["GET"])
def get_tasks():
    return jsonify({"tasks": tasks}), 200

from datetime import datetime, timedelta

@app.route("/schedule", methods=["POST"])
def schedule_tasks():
    current_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    scheduled = []
    blocked_times = []

    # Schedule fixed tasks first
    for task in tasks:
        if task.get("fixed"):
            if "start_time" not in task:
                task_title = task.get("title", "<unnamed task>")
                return jsonify({"error": f"Fixed task '{task_title}' is missing a start_time."}), 400

            start = datetime.strptime(task["start_time"], "%H:%M")
            end = start + timedelta(minutes=task["duration"])
            blocked_times.append((start, end))
            scheduled.append({
                **task,
                "start_time": task["start_time"],
                "end_time": end.strftime("%H:%M")
            })

    # Now schedule flexible tasks
    for task in tasks:
        if task.get("fixed"):
            continue

        duration = task.get("duration", 60)

        while True:
            proposed_start = current_time
            proposed_end = proposed_start + timedelta(minutes=duration)

            # Check for overlap
            conflict = False
            for block_start, block_end in blocked_times:
                if proposed_start < block_end and proposed_end > block_start:
                    # Move current time to the end of this block and re-check
                    current_time = block_end
                    conflict = True
                    break

            if not conflict:
                break

        # No overlap found — schedule it
        blocked_times.append((current_time, current_time + timedelta(minutes=duration)))
        scheduled.append({
            **task,
            "start_time": current_time.strftime("%H:%M"),
            "end_time": (current_time + timedelta(minutes=duration)).strftime("%H:%M")
        })
        current_time += timedelta(minutes=duration)

    return jsonify({"scheduled": scheduled}), 200


@app.route("/reset-tasks", methods=["POST"])
def reset_tasks():
    tasks.clear()
    return jsonify({"status": "cleared"}), 200

if __name__ == '__main__':
    app.run(debug=True)