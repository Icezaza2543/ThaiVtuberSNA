import { resolve } from 'path'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  base: './',
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    open: '/registry.html',
  },
  build: {
    rollupOptions: {
      input: {
        registry: resolve(__dirname, 'registry.html'),
      },
    },
  },
})
