/** 本地预览静态演示版：把 dist-demo 挂到 /tanhui-longyuan/ 子路径，模拟 GitHub Pages。 */
import http from 'node:http'
import fs from 'node:fs'
import path from 'node:path'

const ROOT = path.resolve('dist-demo')
const PREFIX = '/tanhui-longyuan'
const PORT = 4188
const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon', '.woff': 'font/woff', '.woff2': 'font/woff2'
}

http.createServer((req, res) => {
  let urlPath = decodeURIComponent((req.url || '/').split('?')[0])
  if (!urlPath.startsWith(PREFIX)) {
    res.writeHead(302, { Location: PREFIX + '/' }); res.end(); return
  }
  let rel = urlPath.slice(PREFIX.length) || '/'
  if (rel === '/') rel = '/index.html'
  let file = path.join(ROOT, rel)
  // SPA fallback
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(ROOT, 'index.html')
  const ext = path.extname(file).toLowerCase()
  res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' })
  fs.createReadStream(file).pipe(res)
}).listen(PORT, '127.0.0.1', () => {
  console.log(`Demo server: http://127.0.0.1:${PORT}/tanhui-longyuan/`)
})
