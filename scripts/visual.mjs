import { chromium } from 'playwright'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'

const BASE = process.env.SMOKE_BASE || 'http://127.0.0.1:5173'
const targets = process.argv.slice(2)
const pages = targets.length
  ? targets.map((item) => {
      const [pathName, name] = item.split('=')
      return { pathName, name: name || pathName.replace(/\W+/g, '-') }
    })
  : [
      { pathName: '/', name: 'home' },
      { pathName: '/aid', name: 'aid' },
      { pathName: '/origin', name: 'origin' },
      { pathName: '/green', name: 'green' }
    ]

await mkdir('artifacts', { recursive: true })
const browser = await chromium.launch({ channel: 'msedge', headless: true })
const mobile = process.env.MOBILE === '1'
const context = await browser.newContext({
  viewport: mobile ? { width: 390, height: 844 } : { width: 1440, height: 1000 },
  isMobile: mobile
})
const page = await context.newPage()
const errors = []
page.on('console', (message) => {
  if (message.type() === 'error') errors.push(message.text())
})
page.on('pageerror', (error) => errors.push(error.message))

for (const target of pages) {
  await page.goto(`${BASE}${target.pathName}`, { waitUntil: 'load' })
  await page.waitForTimeout(900)
  const file = path.join('artifacts', `visual-${target.name}.png`)
  await page.screenshot({ path: file, fullPage: true })
  console.log(file)
}
console.log(JSON.stringify({ errors }, null, 2))
await browser.close()
