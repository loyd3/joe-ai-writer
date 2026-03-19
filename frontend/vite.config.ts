import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  optimizeDeps: {
    include: ['vuedraggable']
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq, req) => {
            // 确保将前端的 Authorization 头转发到后端，避免 401 误判
            const auth = req.headers['authorization']
            if (auth) {
              proxyReq.setHeader('Authorization', auth)
            }
          })
        }
      }
    }
  }
})