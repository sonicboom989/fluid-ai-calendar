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

The web UI lets you add tasks, generate schedules and view them on an interactive calendar.
