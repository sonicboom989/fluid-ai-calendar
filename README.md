# fluid-ai-calendar
An AI-powered adaptive, time-blocking calendar that uses chat input and intelligent rescheduling.

## Running

### Backend

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start the server:

```bash
python src/app.py
```

The backend listens on [http://localhost:5000](http://localhost:5000).

### Frontend

1. Install dependencies:

```bash
cd frontend
npm install
```

2. Start the development server:

```bash
npm run dev
```

This launches a modern React interface at [http://localhost:5173](http://localhost:5173) which proxies API requests to the Flask backend.

Set an `OPENAI_API_KEY` in your environment to enable the prompt-based assistant. Use the "Tell the AI about a task" field in the web UI to describe tasks in natural language and have them scheduled automatically. The web interface also supports manual task entry and renders the computed schedule on an interactive calendar.
