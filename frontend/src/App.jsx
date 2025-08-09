import { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Box,
  TextField,
  Button,
  MenuItem,
  FormControlLabel,
  Checkbox,
  Stack,
  CssBaseline
} from '@mui/material';
import FullCalendar from '@fullcalendar/react';
import timeGridPlugin from '@fullcalendar/timegrid';
import './App.css';

function App() {
  const [title, setTitle] = useState('');
  const [duration, setDuration] = useState('');
  const [priority, setPriority] = useState('medium');
  const [fixed, setFixed] = useState(false);
  const [startTime, setStartTime] = useState('');
  const [events, setEvents] = useState([]);
  const [prompt, setPrompt] = useState('');

  const fetchSchedule = () => {
    fetch('/schedule', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    })
      .then((res) => res.json())
      .then((data) => {
        const ev = (data.scheduled || []).map((item) => {
          const start = `${item.date}T${item.start_time}`;
          const end = `${item.date}T${item.end_time}`;
          let color = '#f1c40f';
          if (item.priority === 'high') color = '#e74c3c';
          else if (item.priority === 'low') color = '#27ae60';
          return {
            title: item.title,
            start,
            end,
            backgroundColor: color,
            borderColor: color
          };
        });
        setEvents(ev);
      });
  };

  useEffect(() => {
    fetchSchedule();
  }, []);

  const handlePromptSubmit = (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    fetch('/natural-schedule', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt })
    })
      .then(() => {
        setPrompt('');
        fetchSchedule();
      });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const payload = {
      title,
      duration: parseInt(duration, 10),
      priority,
      fixed
    };
    if (fixed && startTime) {
      payload.start_time = startTime;
    }
    fetch('/add-task', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(() => {
      setTitle('');
      setDuration('');
      setPriority('medium');
      setFixed(false);
      setStartTime('');
      fetchSchedule();
    });
  };

  return (
    <>
      <CssBaseline />
      <Container sx={{ py: 4 }}>
        <Typography variant="h4" gutterBottom>
          Fluid AI Calendar
        </Typography>
        <Box component="form" onSubmit={handlePromptSubmit} sx={{ mb: 4 }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="center">
            <TextField
              label="Tell the AI about a task"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              fullWidth
            />
            <Button type="submit" variant="contained">
              Ask AI
            </Button>
          </Stack>
        </Box>
        <Box component="form" onSubmit={handleSubmit} sx={{ mb: 4 }}>
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={2}
            alignItems="center"
          >
            <TextField
              label="Title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
            <TextField
              label="Duration (min)"
              type="number"
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              required
            />
            <TextField
              select
              label="Priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              sx={{ minWidth: 120 }}
            >
              <MenuItem value="low">Low</MenuItem>
              <MenuItem value="medium">Medium</MenuItem>
              <MenuItem value="high">High</MenuItem>
            </TextField>
            <FormControlLabel
              control={
                <Checkbox
                  checked={fixed}
                  onChange={(e) => setFixed(e.target.checked)}
                />
              }
              label="Fixed time"
            />
            {fixed && (
              <TextField
                type="time"
                label="Start"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                inputProps={{ step: 300 }}
              />
            )}
            <Button type="submit" variant="contained">
              Add Task
            </Button>
          </Stack>
        </Box>
        <Button variant="outlined" onClick={fetchSchedule} sx={{ mb: 2 }}>
          Refresh Schedule
        </Button>
        <FullCalendar
          plugins={[timeGridPlugin]}
          initialView="timeGridWeek"
          events={events}
          height="auto"
        />
      </Container>
    </>
  );
}

export default App;
