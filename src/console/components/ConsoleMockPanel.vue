<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { useConsoleApp } from '@/console/stores/app'

const app = useConsoleApp()

async function resetData(): Promise<void> {
  try {
    await ElMessageBox.confirm(
      '将清空当前内存中的演示数据并恢复到初始种子状态，确定继续吗？',
      '重置演示数据',
      { type: 'warning', confirmButtonText: '重置并刷新', cancelButtonText: '取消' }
    )
    app.resetMock()
  } catch {
    // 取消
  }
}

function toggle(value: boolean): void {
  app.setMockFail(value)
  ElMessage.info(value ? '已开启偶发失败（约 10%）' : '已关闭偶发失败')
}
</script>

<template>
  <el-popover placement="bottom-end" :width="240" trigger="click">
    <template #reference>
      <button type="button" class="console-icon-button" title="Mock 数据设置">
        <el-icon><DataLine /></el-icon>
      </button>
    </template>
    <div class="console-mock-popover">
      <h4>Mock 数据</h4>
      <p>所有请求 300–600ms 延迟，数据仅存于浏览器本地；后续替换 api 层即可接真实接口。</p>
      <div class="console-switch-row">
        <span>偶发失败（约 10%）</span>
        <el-switch :model-value="app.mockFail" size="small" @update:model-value="toggle" />
      </div>
      <el-button link type="danger" size="small" @click="resetData">重置演示数据</el-button>
    </div>
  </el-popover>
</template>
