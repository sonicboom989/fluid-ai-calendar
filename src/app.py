from flask import Flask, request, jsonify
import uuid
from scheduler import Scheduler

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
    payload   = request.get_json() or {}
    scheduler = Scheduler()

    # Re-add all stored tasks
    for task in tasks:
        scheduler.add_task(task)

    # If the client provided a goal, inject hybrid blocks
    goal = payload.get("goal")
    if goal:
        scheduler.add_goal_hybrid(
            title          = goal["title"],
            total_minutes  = goal["total_minutes"],
            max_block_size = goal["max_block_size"],
            priority       = goal.get("priority", "medium")
        )

    # Run and return your schedule
    try:
        result = scheduler.schedule()
        return jsonify({"scheduled": result}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400




@app.route("/reset-tasks", methods=["POST"])
def reset_tasks():
    tasks.clear()
    return jsonify({"status": "cleared"}), 200

if __name__ == '__main__':
    app.run(debug=True)