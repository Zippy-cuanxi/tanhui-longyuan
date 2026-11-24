/**
 * 首屏预渲染骨架（prerender shell）
 * =================================
 * SPA 的首屏内容完全依赖 JS 下载 + 执行后才出现，移动端 4G 下 FCP 被拖到 1.8s 左右。
 * 本脚本在构建完成后用真实浏览器打开构建产物，等首页完整渲染后把 #app 的 HTML
 * 快照内联进 index.html；浏览器解析 HTML 时即可直接绘制首屏（含顶部导航、轮播、
 * 商品与产地地图），Vue 启动后 mount() 会用完全相同的 DOM 替换骨架。
 *
 * - 仅处理 index.html；404.html 保持空壳，避免深链接先闪一下首页内容。
 * - 构建产物与首屏骨架不一致（例如接口挂了）时只告警，不影响部署。
 * - 依赖本机 Chrome（CI 的 ubuntu-latest 自带），找不到时回退到 Playwright Chromium。
 *
 * 用法：node scripts/prerender-shell.mjs [distDir]
 */
import { createServer } from 'node:http'
import { createReadStream, existsSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import { extname, join, normalize, resolve } from 'node:path'
import Beasties from 'beasties'
import { chromium } from 'playwright'

const distDir = resolve(process.argv[2] || 'dist-demo')
const indexPath = join(distDir, 'index.html')

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.webp': 'image/webp',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2',
  '.ico': 'image/x-icon'
}

function fail(message) {
  console.warn(`[prerender] ${message}；跳过首屏骨架，构建继续。`)
  process.exit(0)
}

if (!existsSync(indexPath)) fail(`未找到 ${indexPath}`)

const originalHtml = readFileSync(indexPath, 'utf8')

// 从入口 script 反推部署 base（GitHub Pages 为 /<repo>/）
const entryMatch = originalHtml.match(/<script[^>]+type="module"[^>]+src="([^"]+)"/)
if (!entryMatch) fail('无法从 index.html 定位入口脚本')
const entrySrc = entryMatch[1]
const base = entrySrc.slice(0, entrySrc.indexOf('assets/')) || '/'

/* ---------------- 静态文件服务（把 dist 挂到部署 base 下） ---------------- */
const server = createServer((req, res) => {
  let pathname = decodeURIComponent((req.url || '/').split('?')[0])
  if (base !== '/' && pathname.startsWith(base)) pathname = pathname.slice(base.length)
  if (!pathname.startsWith('/')) pathname = `/${pathname}`
  if (pathname === '/' || !extname(pathname)) pathname = '/index.html'
  const file = normalize(join(distDir, pathname))
  if (!file.startsWith(distDir) || !existsSync(file) || !statSync(file).isFile()) {
    res.writeHead(404)
    res.end('not found')
    return
  }
  res.writeHead(200, {
    'Content-Type': MIME[extname(file).toLowerCase()] || 'application/octet-stream'
  })
  createReadStream(file).pipe(res)
})

const port = await new Promise((resolvePort, rejectPort) => {
  server.on('error', rejectPort)
  server.listen(0, '127.0.0.1', () => resolvePort(server.address().port))
})

async function launchBrowser() {
  const args = ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
  try {
    return await chromium.launch({ channel: 'chrome', headless: true, args })
  } catch {
    return chromium.launch({ headless: true, args })
  }
}

let browser
try {
  browser = await launchBrowser()
} catch (error) {
  server.close()
  fail(`无法启动浏览器（${error.message}）`)
}

const url = `http://127.0.0.1:${port}${base}`
let shell = ''
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
  const page = await context.newPage()
  // 关闭入场动画/过渡，保证快照就是内容最终态，且不会拍到动画中间帧
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto(url, { waitUntil: 'load', timeout: 30000 })
  await page.waitForSelector('.site-header', { timeout: 15000 })
  await page.waitForSelector('.home-carousel', { timeout: 15000 })
  await page.waitForTimeout(300)

  /**
   * 只内联「顶部导航 + 轮播占位」：
   * - 顶部导航是每家页面完全一致的静态结构，首帧即可绘制；
   * - 轮播位用与真实轮播同尺寸/同底色的占位块撑住布局（不含图片，避免成为新的 LCP 元素
   *   后被 Vue 挂载重建、把 LCP 时间点推迟到二次渲染）；
   * - 首屏以下的商品/地图等内容不放进骨架，挂载后自然出现，避免首屏为这些内容做一次
   *   昂贵的布局再重来一次。
   */
  shell = await page.evaluate(() => {
    const header = document.querySelector('.site-header')?.outerHTML
    if (!header) return ''
    return (
      '<div class="app-shell">' +
      header +
      '<main class="page-main home-page"><div class="page-container">' +
      '<div aria-hidden="true" style="aspect-ratio:3.158;border-radius:var(--radius-lg);' +
      'background:#dcefe3;box-shadow:0 8px 28px rgba(16,99,52,.09)"></div>' +
      '</div></main></div>'
    )
  })
  await context.close()
} catch (error) {
  console.warn(`[prerender] 快照失败：${error.message}`)
} finally {
  await browser.close()
  server.close()
}

if (!shell || shell.length < 2000) {
  fail(`首屏骨架内容异常（${shell.length} 字符）`)
}

/* ---------------- 组装 index.html ---------------- */
const preloadTags = []
const seen = new Set()

const manifestPath = join(distDir, '.vite/manifest.json')
if (existsSync(manifestPath)) {
  try {
    const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'))
    const collect = (key) => {
      if (key === 'index.html') return
      const item = manifest[key]
      if (!item || seen.has(item.file)) return
      seen.add(item.file)
      preloadTags.push(`<link rel="modulepreload" crossorigin href="${base}${item.file}">`)
      for (const dep of item.imports || []) collect(dep)
    }
    // 首页路由及其所有静态依赖（Vite 原本要等入口执行后才发现这些 chunk）
    collect('src/views/HomeView.vue')
    collect('src/api/heat.ts')
  } catch (error) {
    console.warn(`[prerender] 读取 manifest 失败：${error.message}`)
  }
}

const imagePreloads = [
  // 只预加载首屏 LCP 图；其余横幅/地图数据晚点加载，避免和入口 JS 抢慢速带宽
  `<link rel="preload" as="image" href="${base}images/banners/home-main-visual.webp" fetchpriority="high">`
]

let nextHtml = originalHtml.replace('<html ', '<html data-prerender="1" ')
// 用函数式替换，避免骨架里的 `$` 被当成 replace 的占位符
nextHtml = nextHtml.replace(/<div id="app"><\/div>/, () => `<div id="app">${shell}</div>`)
nextHtml = nextHtml.replace('</head>', () => `${[...preloadTags, ...imagePreloads].join('')}</head>`)

if (!nextHtml.includes('data-prerender="1"') || !nextHtml.includes(shell.slice(0, 200))) {
  fail('index.html 注入失败（未找到挂载点）')
}

// 关键 CSS 内联：只把首屏骨架用到的规则放进 <style>，其余样式表改为非阻塞加载。
// 否则 128KB 全局样式会一直阻塞首次绘制（Lighthouse 移动端 FCP 的主要来源）。
let critiqued = nextHtml
try {
  const beasties = new Beasties({
    path: distDir,
    publicPath: base,
    preload: 'swap',
    pruneSource: false,
    inlineThreshold: 0,
    minimumExternalSize: 0,
    logLevel: 'warn'
  })
  critiqued = await beasties.process(nextHtml)
} catch (error) {
  console.warn(`[prerender] 关键 CSS 内联失败，保留阻塞式样式表：${error.message}`)
}

writeFileSync(indexPath, critiqued)
const kb = (n) => `${(n / 1024).toFixed(1)}kB`
console.log(
  `[prerender] 首屏骨架已内联：${kb(shell.length)}（HTML ${kb(originalHtml.length)} → ${kb(critiqued.length)}，modulepreload ${preloadTags.length} 条，关键 CSS ${critiqued !== nextHtml ? '已内联' : '未内联'}）`
)
