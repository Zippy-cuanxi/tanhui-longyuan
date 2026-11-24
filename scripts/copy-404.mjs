// 复制 index.html 为 404.html，使 GitHub Pages 上的 SPA 深链接可回落到前端路由。
// 用法：node scripts/copy-404.mjs [distDir]
import { copyFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

const distDir = process.argv[2] || 'dist-demo'
const index = resolve(distDir, 'index.html')
const fallback = resolve(distDir, '404.html')

if (!existsSync(index)) {
  console.error(`[copy-404] 未找到 ${index}，请先执行构建`)
  process.exit(1)
}

copyFileSync(index, fallback)
console.log(`[copy-404] ${index} -> ${fallback}`)
