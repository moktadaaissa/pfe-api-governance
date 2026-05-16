import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: ["repair-remember-dismount.ngrok-free.dev"],
    proxy: {
      '/auth':           { target: 'http://localhost:8000', changeOrigin: true },
      '/upload-openapi': { target: 'http://localhost:8000', changeOrigin: true },
      '/publish-openapi':{ target: 'http://localhost:8000', changeOrigin: true },
      '/download-fixed': { target: 'http://localhost:8000', changeOrigin: true },
      '/catalog':        { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
