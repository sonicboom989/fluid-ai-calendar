# fluid-ai-calendar
An AI-powered adaptive, time-blocking calendar that uses chat input and intelligent rescheduling.

## Running

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Ensure an OpenAI API key is available:

```bash
export OPENAI_API_KEY="your-key"
```

3. Start the server:

```bash
python src/app.py
```

4. Open [http://localhost:5000](http://localhost:5000) in your browser to use the web interface.

Use the prompt box to describe tasks in natural language ("Schedule a 30‑minute call tomorrow at 2 PM") and the assistant will add and schedule them automatically on the interactive calendar.
