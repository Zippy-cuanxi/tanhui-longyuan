import { chromium } from 'playwright'

const BASE = process.env.SMOKE_BASE || 'http://127.0.0.1:5173'
const browser = await chromium.launch({ channel: 'msedge', headless: true })
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })
const logs = []
page.on('console', (m) => logs.push(`console.${m.type()}: ${m.text()}`))
page.on('pageerror', (e) => logs.push(`pageerror: ${e.stack || e.message}`))
page.on('requestfailed', (r) =>
  logs.push(`requestfailed: ${r.url()} :: ${r.failure()?.errorText || ''}`),
)
page.on('response', (r) => {
  if (r.status() >= 400) logs.push(`http ${r.status()}: ${r.url()}`)
})
await page
  .goto(`${BASE}/`, { waitUntil: 'load', timeout: 20000 })
  .catch((e) => logs.push('goto: ' + e.message))
await page.waitForTimeout(2500)
const info = await page.evaluate(() => ({
  title: document.title,
  bodyText: document.body.innerText.slice(0, 600),
  appHtml: document.querySelector('#app')?.innerHTML.slice(0, 400) || '',
  scripts: [...document.querySelectorAll('script')].map((s) => s.src || 'inline'),
  styles: [...document.querySelectorAll('link[rel=stylesheet]')].map((l) => l.href),
  bodyBg: getComputedStyle(document.body).backgroundColor,
}))
await page.screenshot({ path: 'artifacts/diagnose-5173.png', fullPage: true })
console.log(JSON.stringify({ info, logs }, null, 2))
await browser.close()
