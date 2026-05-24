import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import WindiCSS from 'vite-plugin-windicss'

const FRONTEND_HOST = '127.0.0.1'
const FRONTEND_PORT = 3099
const BACKEND_URL = 'http://127.0.0.1:8099'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue(), WindiCSS()],
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
