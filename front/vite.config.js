import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import WindiCSS from 'vite-plugin-windicss'

const FRONTEND_HOST = process.env.MANISCOPE_FRONTEND_HOST || '127.0.0.1'
const FRONTEND_PORT = Number(process.env.MANISCOPE_FRONTEND_PORT || 3099)
const BACKEND_URL = process.env.MANISCOPE_BACKEND_PROXY_TARGET || 'http://127.0.0.1:8099'
const PUBLIC_DIR = process.env.MANISCOPE_DISABLE_PUBLIC_COPY === '1' ? false : 'public'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue(), WindiCSS()],
  publicDir: PUBLIC_DIR,
  server: {
    host: FRONTEND_HOST,
    port: FRONTEND_PORT,
    strictPort: true,
    proxy: {
      '/api': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
    },
  },
})
