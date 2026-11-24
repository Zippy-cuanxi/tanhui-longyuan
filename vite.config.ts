import { readFileSync } from 'node:fs'
import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// 默认联调 8000；.env.local 或环境变量 VITE_PROXY_TARGET 可覆盖。
// 优先读取 .env.local，其次读取进程环境变量。
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const proxyTarget =
    env.VITE_PROXY_TARGET || process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000'

  const isDemo = env.VITE_STATIC_DEMO === '1' || process.env.VITE_STATIC_DEMO === '1'
  // GitHub Pages 项目站点部署在 /<repo>/ 子路径下；静态演示模式自动使用该 base。
  const base = isDemo ? '/tanhui-longyuan/' : '/'

  // 静态演示快照直接打进 demoAdapter chunk，避免 GitHub Pages 上额外请求 JSON 造成首屏空白。
  const demoSnapshotPath = fileURLToPath(new URL('./public/demo-data.json', import.meta.url))
  const inlineDemoSnapshot = {
    name: 'inline-demo-snapshot',
    resolveId(id: string) {
      if (id === 'virtual:demo-snapshot') return '\0virtual:demo-snapshot'
      return null
    },
    load(id: string) {
      if (id === '\0virtual:demo-snapshot') {
        return `export default ${readFileSync(demoSnapshotPath, 'utf8')}`
      }
      return null
    }
  }

  return {
    plugins: [vue(), inlineDemoSnapshot],
    base,
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true
        },
        '/uploads': {
          target: proxyTarget,
          changeOrigin: true
        }
      }
    },
    preview: {
      port: 4173,
      strictPort: true
    }
  }
})
