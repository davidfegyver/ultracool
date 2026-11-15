import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // dev against the production stack (read-only): VITE_API_TARGET=http://localhost:8080 npx vite
  server: { proxy: { '/api': process.env.VITE_API_TARGET ?? 'http://localhost:8000' } },
})
