import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/add-task': 'http://localhost:5000',
      '/get-tasks': 'http://localhost:5000',
      '/schedule': 'http://localhost:5000',
      '/natural-schedule': 'http://localhost:5000'
    }
  }
})
