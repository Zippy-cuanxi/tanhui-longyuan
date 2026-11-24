import { getCurrentInstance } from 'vue'
import type { App } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import './styles/console.css'

let installed = false

/** 只在首次进入 /console 时安装 Element Plus / 图标 / 主题，不进入消费者首屏。 */
export function installConsoleUI(app: App): void {
  if (installed) return
  installed = true
  app.use(ElementPlus, { locale: zhCn })
  Object.entries(ElementPlusIconsVue).forEach(([name, component]) => {
    app.component(name, component)
  })
  document.body.classList.add('console-mode')
}

export function useConsoleUi(): void {
  const instance = getCurrentInstance()
  if (instance) installConsoleUI(instance.appContext.app)
}
