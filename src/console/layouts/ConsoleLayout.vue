<script setup lang="ts">
import { computed } from 'vue'
import { useConsoleUi } from '@/console/install'
import { useConsoleAuth } from '@/console/stores/auth'
import { useConsoleApp } from '@/console/stores/app'
import { menuForRole } from '@/console/constants/menu'
import ConsoleSidebar from '@/console/components/ConsoleSidebar.vue'
import ConsoleTopbar from '@/console/components/ConsoleTopbar.vue'

useConsoleUi()

const auth = useConsoleAuth()
const app = useConsoleApp()
const menus = computed(() => menuForRole(auth.isAdmin ? 'admin' : 'merchant', auth.permissions))
</script>

<template>
  <div class="console-shell">
    <ConsoleSidebar :menus="menus" :collapsed="app.collapsed" />
    <div class="console-main">
      <ConsoleTopbar :collapsed="app.collapsed" @toggle="app.toggleCollapsed" />
      <main class="console-content">
        <RouterView />
      </main>
    </div>
  </div>
</template>
