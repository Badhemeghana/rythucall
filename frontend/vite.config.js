import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/farmer': 'http://127.0.0.1:8000',
      '/village': 'http://127.0.0.1:8000',
      '/booking': 'http://127.0.0.1:8000',
    },
  },
})
