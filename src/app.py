from flask import Flask, request, jsonify
import uuid
from scheduler import Scheduler
#For AI route
import os
import json
from openai import OpenAI



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


@app.route("/ai-schedule", methods=["POST"])
def ai_schedule():
    payload   = request.get_json() or {}
    scheduler = Scheduler()

    #Re-add all stored tasks so we keep pre-existing items
    for t in tasks:
        scheduler.add_task(t)

    # Apply any “actions” the client sent
    #    Each action is a dict with a "type" and its parameters.
    for action in payload.get("actions", []):
        typ = action.get("type")
        if typ == "add_task":
            # expects: { "type":"add_task", "task": { … } }
            scheduler.add_task(action["task"])
        elif typ == "add_goal_hybrid":
            # expects keys: title, total_minutes, max_block_size, [priority]
            scheduler.add_goal_hybrid(
                title          = action["title"],
                total_minutes  = action["total_minutes"],
                max_block_size = action["max_block_size"],
                priority       = action.get("priority", "medium")
            )
        else:
            return jsonify({
              "error": f"Unknown action type: {typ}"
            }), 400

    # 3 Run the scheduler and return the result
    try:
        result = scheduler.schedule()
        return jsonify({"scheduled": result}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    



openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/natural-schedule", methods=["POST"])
def natural_schedule():
    data = request.get_json() or {}
    user_prompt = data.get("prompt", "").strip()
    if not user_prompt:
        return jsonify({"error": "Missing 'prompt' in request body."}), 400

    # 1️⃣ Build the messages for the LLM
    system_msg = """
        You are an AI calendar assistant.  You must parse the user's instruction and
        output **only** a JSON object with an "actions" array.  There are three action
        types:

        1) add_task  
        • "title": string  
        • "duration": number (minutes)  
        • "fixed": boolean  
        • "start_time": "HH:MM" (if fixed==true)  

        If the user mentions a specific time (e.g. "10:30 meeting"), you must:
            – set fixed=true  
            – set start_time to that time  
            – assume duration=60 unless otherwise specified  

        2) add_goal_hybrid  
        • "title": string  
        • "total_minutes": number  
        • "max_block_size": number  
        • "priority": string (optional, default "medium")  

        3) add_rest  
        • Insert a rest block between tasks  
        • Include:
            – "duration": number (minutes)  
            – "title": "Rest"  
            – "fixed": false  

        Use this action when the user asks for a rest period (e.g. "Add 2 hours of rest between each block").

        **Example**  
        User prompt:  
        "Schedule my morning around a 10:30 meeting, give me 2 hours for my side project, and add 2 hours of rest between each block."

        Correct JSON response:
        ```json
        {
        "actions": [
            {
            "type": "add_task",
            "task": {
                "title":      "Meeting",
                "duration":    60,
                "fixed":       true,
                "start_time": "10:30"
            }
            },
            {
            "type": "add_rest",
            "duration": 120,
            "title":    "Rest",
            "fixed":    false
            },
            {
            "type": "add_goal_hybrid",
            "title":           "Side project",
            "total_minutes":   120,
            "max_block_size":  60
            },
            {
            "type": "add_rest",
            "duration": 120,
            "title":    "Rest",
            "fixed":    false
            }
        ]
        }

        DO not wrap your response in markdown or any extra keys—just emit the raw JSON object.
        """
    
    existing = json.dumps(tasks)
    messages = [
    {"role":"system",    "content": system_msg},
    {"role":"assistant", "content": f"Existing tasks: {existing}"},
    {"role":"user",      "content": request.json.get("prompt","")}
    ]

    resp = openai_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    temperature=0
    )
    content = resp.choices[0].message.content

    # 3️⃣ Parse the LLM’s JSON
    try:
        payload = json.loads(content)
        actions = payload.get("actions", [])
    except json.JSONDecodeError:
        return jsonify({
            "error": "Could not parse LLM response as JSON",
            "raw_response": content
        }), 500

    # 4️⃣ Replay actions through your Scheduler
    scheduler = Scheduler()
    for t in tasks:
        scheduler.add_task(t)

    for a in actions:
        typ = a.get("type")
        if typ == "add_task":
            # support both {"type":"add_task","task": {...}}
            # and flattened {"type":"add_task", "title":..., "duration":..., ...}
            if "task" in a:
                task = a["task"]
            else:
                # take all keys except "type" as the task dict
                task = {k: v for k, v in a.items() if k != "type"}
            scheduler.add_task(task)

        elif typ == "add_goal_hybrid":
            scheduler.add_goal_hybrid(
                title          = a["title"],
                total_minutes  = a["total_minutes"],
                max_block_size = a["max_block_size"],
                priority       = a.get("priority", "medium")
            )

        elif typ == "add_rest":
            # a should have "duration" (and optional "title")
            scheduler.add_task({
                "title":    a.get("title", "Rest"),
                "duration": a["duration"],
                "fixed":    False
            })

        else:
            return jsonify({"error": f"Unknown action type '{typ}'"}), 400

    # 5️⃣ Generate and return the final, chronological schedule
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