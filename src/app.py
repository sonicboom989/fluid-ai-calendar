from flask import Flask, request, jsonify, render_template
import uuid
from scheduler import Scheduler
#For AI route
import os
import json
from openai import OpenAI
from datetime import datetime, timedelta, date



app = Flask(__name__, static_folder="static", template_folder="templates")

tasks = []

@app.route('/')
def home():
    return render_template('index.html')

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

    # 1) Re-add all stored tasks
    for t in tasks:
        scheduler.add_task(t)

    # 2) Hybrid goal (single-day) if provided
    goal = payload.get("goal")
    if goal:
        scheduler.add_goal_hybrid(
            title          = goal["title"],
            total_minutes  = goal["total_minutes"],
            max_block_size = goal["max_block_size"],
            priority       = goal.get("priority", "medium")
        )

    # 3) Periodic goal (multi-day) if provided
    periodic = payload.get("periodic_goal")
    if periodic:
        sd = datetime.strptime(periodic["start_date"], "%Y-%m-%d").date()
        ed = datetime.strptime(periodic["end_date"],   "%Y-%m-%d").date()
        scheduler.add_goal_periodic(
            title          = periodic["title"],
            total_minutes  = periodic["total_minutes"],
            max_block_size = periodic["max_block_size"],
            start_date     = sd,
            end_date       = ed,
            rest_between   = periodic.get("rest_between", 0),
            priority       = periodic.get("priority", "medium")
        )

    # 4) Run the scheduler and return the result
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
            tasks.append(action["task"])
        elif typ == "add_goal_hybrid":
            # expects keys: title, total_minutes, max_block_size, [priority]
            scheduler.add_goal_hybrid(
                title          = action["title"],
                total_minutes  = action["total_minutes"],
                max_block_size = action["max_block_size"],
                priority       = action.get("priority", "medium")
            )
        elif typ == "add_goal_periodic":
            sd = datetime.strptime(action["start_date"], "%Y-%m-%d").date()
            ed = datetime.strptime(action["end_date"],   "%Y-%m-%d").date()
            scheduler.add_goal_periodic(
                title          = action["title"],
                total_minutes  = action["total_minutes"],
                max_block_size = action["max_block_size"],
                start_date     = sd,
                end_date       = ed,
                rest_between   = action.get("rest_between", 0),
                priority       = action.get("priority", "medium")
            )
        elif typ == "move_task":
            scheduler.move_task(action["task_id"],
                                action.get("earliest_time"),
                                action.get("latest_time"))
            for t in tasks:
                if t.get("id") == action["task_id"]:
                    if action.get("earliest_time"):
                        t["earliest_time"] = action["earliest_time"]
                    if action.get("latest_time"):
                        t["latest_time"] = action["latest_time"]
                    break
        elif typ == "remove_task":
            scheduler.remove_task(action["task_id"])
            tasks[:] = [t for t in tasks if t.get("id") != action["task_id"]]
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
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "Missing 'prompt' in request body."}), 400

    # 1️⃣ Build the messages for the LLM (now including add_goal_periodic)
    system_msg = """
You are an AI calendar assistant. You receive existing tasks and a user instruction,
and must output ONLY a JSON object with an \"actions\" array. Valid actions:

  • add_task
    – Nested: { \"type\":\"add_task\", \"task\":{…} }
    – or flattened: { \"type\":\"add_task\", \"title\":…, \"duration\":…, \"fixed\":…, [\"start_time\"] }

  • add_goal_hybrid
    – { \"type\":\"add_goal_hybrid\", \"title\":…, \"total_minutes\":…, \"max_block_size\":…, [\"priority\"] }

  • add_goal_periodic
    – { 
        \"type\":\"add_goal_periodic\",
        \"title\":…,
        \"total_minutes\":…,
        \"max_block_size\":…,
        \"start_date\":\"YYYY-MM-DD\",
      \"end_date\":\"YYYY-MM-DD\",
      [\"rest_between\"],
      [\"priority\"]
      }

  • add_rest
    – { \"type\":\"add_rest\", \"duration\":…, \"title\":\"Rest\", \"fixed\":false }

  • move_task
    – { \"type\":\"move_task\", \"task_id\":…, \"earliest_time\":\"HH:MM\", \"latest_time\":\"HH:MM\" }

  • remove_task
    – { \"type\":\"remove_task\", \"task_id\":… }

Do NOT wrap in Markdown or include any extra keys—emit exactly:

```json
{ \"actions\":[ /* your action objects here */ ] }
Example
User: "Schedule 5 hours of side-project between 2025-07-20 and 2025-07-24 in 2h chunks with 30m rest."
Should output:
{
  \"actions\": [
    {
      \"type\": \"add_goal_periodic\",
      \"title\": \"Side project\",
      \"total_minutes\": 300,
      \"max_block_size\": 120,
      \"start_date\": \"2025-07-20\",
      \"end_date\": \"2025-07-24\",
      \"rest_between\": 30
    }
  ]
}
"""
    existing = json.dumps(tasks)
    messages = [
        {"role": "system",    "content": system_msg},
        {"role": "assistant", "content": f"Existing tasks: {existing}"},
        {"role": "user",      "content": prompt},
    ]

    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0
    )
    content = resp.choices[0].message.content

    # 2️⃣ Parse the LLM’s JSON
    try:
        payload = json.loads(content)
        actions = payload.get("actions", [])
    except json.JSONDecodeError:
        return jsonify({
            "error": "Could not parse LLM response as JSON",
            "raw_response": content
        }), 500

    # 3️⃣ Replay actions through your Scheduler
    scheduler = Scheduler()
    for t in tasks:
        scheduler.add_task(t)

    for a in actions:
        typ = a.get("type")
        if typ == "add_task":
            task = a.get("task") or {k: v for k, v in a.items() if k != "type"}
            scheduler.add_task(task)
            tasks.append(task)

        elif typ == "add_goal_hybrid":
            scheduler.add_goal_hybrid(
                title          = a["title"],
                total_minutes  = a["total_minutes"],
                max_block_size = a["max_block_size"],
                priority       = a.get("priority", "medium")
            )

        elif typ == "add_goal_periodic":
            # parse dates and call the periodic helper
            sd = datetime.strptime(a["start_date"], "%Y-%m-%d").date()
            ed = datetime.strptime(a["end_date"],   "%Y-%m-%d").date()
            scheduler.add_goal_periodic(
                title          = a["title"],
                total_minutes  = a["total_minutes"],
                max_block_size = a["max_block_size"],
                start_date     = sd,
                end_date       = ed,
                rest_between   = a.get("rest_between", 0),
                priority       = a.get("priority", "medium")
            )

        elif typ == "add_rest":
            rest_task = {
                "title":    a.get("title", "Rest"),
                "duration": a["duration"],
                "fixed":    False
            }
            scheduler.add_task(rest_task)
            tasks.append(rest_task)

        elif typ == "move_task":
            scheduler.move_task(a["task_id"], a.get("earliest_time"), a.get("latest_time"))
            for t in tasks:
                if t.get("id") == a["task_id"]:
                    if a.get("earliest_time"):
                        t["earliest_time"] = a["earliest_time"]
                    if a.get("latest_time"):
                        t["latest_time"] = a["latest_time"]
                    break

        elif typ == "remove_task":
            scheduler.remove_task(a["task_id"])
            tasks[:] = [t for t in tasks if t.get("id") != a["task_id"]]

        else:
            return jsonify({"error": f"Unknown action type '{typ}'"}), 400

    # 4️⃣ Generate and return the final schedule
    try:
        scheduled = scheduler.schedule()
        return jsonify({"scheduled": scheduled}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400



@app.route("/reset-tasks", methods=["POST"])
def reset_tasks():
    tasks.clear()
    return jsonify({"status": "cleared"}), 200

if __name__ == '__main__':
    app.run(debug=True)