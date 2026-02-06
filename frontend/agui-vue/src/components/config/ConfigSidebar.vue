<script setup lang="ts">
import type { Component } from 'vue'

export interface NavItem {
  key: string
  label: string
  icon: Component
}

defineProps<{
  activeTab: string
  navItems: NavItem[]
}>()

const emit = defineEmits<{
  'update:activeTab': [value: string]
}>()

function handleNavClick(key: string) {
  emit('update:activeTab', key)
}
</script>

<template>
  <div class="w-64 flex-shrink-0 border-r border-border bg-card/30 flex flex-col">
    <!-- Header -->
    <div class="p-6 border-b border-border">
      <h1 class="text-xl font-bold font-heading text-foreground">AI 配置</h1>
      <p class="text-xs text-muted-foreground mt-1">管理 AI 提供商和全局设置</p>
    </div>

    <!-- Navigation Items -->
    <div class="flex-1 p-3 space-y-1">
      <button
        v-for="item in navItems"
        :key="item.key"
        @click="handleNavClick(item.key)"
        class="w-full flex items-center gap-3 px-4 py-3 rounded-lg cursor-pointer transition-all duration-normal ease-out text-left"
        :class="activeTab === item.key
          ? 'bg-primary/10 text-primary font-medium'
          : 'hover:bg-muted/50 text-muted-foreground hover:text-foreground'"
      >
        <component :is="item.icon" class="size-4 shrink-0" />
        <span class="text-sm">{{ item.label }}</span>
      </button>
    </div>
  </div>
</template>
