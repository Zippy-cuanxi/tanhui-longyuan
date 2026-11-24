import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/main.css'
import './assets/polish.css'

/**
 * 首屏启动时序：
 * 等首个路由组件解析完成后再挂载，避免 App 先渲染页脚、路由内容后插入造成布局抖动（CLS）。
 * 构建产物若内联了预渲染骨架（data-prerender），骨架会一直显示到此刻，用户不会看到空白。
 * 首页地图等首屏以下的数据由各自组件在挂载后再加载，不占用入口 JS 的下载带宽。
 */
async function bootstrap(): Promise<void> {
  const app = createApp(App)
  app.use(createPinia())
  app.use(router)

  try {
    await router.isReady()
  } catch {
    // 首个路由加载/导航失败时仍然挂载，交给路由与页面自身的错误态处理
  }

  app.mount('#app')
}

void bootstrap()
