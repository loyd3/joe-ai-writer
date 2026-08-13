import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

const isWin = process.platform === 'win32'
const apiTarget = process.env.VITE_API_URL || 'http://localhost:8000'
const hmrClientPort = process.env.VITE_HMR_CLIENT_PORT
  ? Number(process.env.VITE_HMR_CLIENT_PORT)
  : undefined

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
    host: true,
    strictPort: false,
    // 前端 HMR：改 Vue/TS/CSS 后浏览器自动热更新，无需重启
    hmr: {
      overlay: true,
      ...(hmrClientPort ? { clientPort: hmrClientPort } : {}),
    },
    watch: {
      // Windows 下部分编辑器保存后监听不稳定时用轮询兜底
      usePolling: isWin,
      interval: isWin ? 300 : undefined,
      ignored: ['**/node_modules/**', '**/dist/**'],
    },
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq, req) => {
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
