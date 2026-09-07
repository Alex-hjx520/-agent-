import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 后端 FastAPI 默认端口：8010（被占用时用 8012/8015，改这里即可）
const BACKEND_PORT = 8010

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // 把 /chat、/health 代理到 FastAPI 后端（/chat 前缀已覆盖 /chat/agent/stream）
      '/chat': {
        target: `http://127.0.0.1:${BACKEND_PORT}`,
        changeOrigin: true,
      },
      '/health': {
        target: `http://127.0.0.1:${BACKEND_PORT}`,
        changeOrigin: true,
      },
      '/parse-doc': {
        target: `http://127.0.0.1:${BACKEND_PORT}`,
        changeOrigin: true,
      },
      '/select': {
        target: `http://127.0.0.1:${BACKEND_PORT}`,
        changeOrigin: true,
      },
      '/flow': {
        target: `http://127.0.0.1:${BACKEND_PORT}`,
        changeOrigin: true,
      },
    },
  },
})
