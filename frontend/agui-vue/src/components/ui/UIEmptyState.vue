<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  icon?: string // Heroicon name
  title?: string
  description?: string
  actionText?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: '暂无数据',
  description: '目前没有可显示的内容',
})

const emit = defineEmits<{
  action: []
}>()

function handleAction() {
  emit('action')
}

// Icon mapping for common icons
const iconPaths: Record<string, string> = {
  document: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  folder: 'M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z',
  search: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z',
  chat: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z',
  database: 'M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4',
}

const iconPath = computed(() => iconPaths[props.icon || 'document'] || iconPaths.document)
</script>

<template>
  <div class="flex flex-col items-center justify-center py-16 px-4 text-center">
    <!-- Icon Container -->
    <div
      class="w-20 h-20 rounded-2xl bg-muted flex items-center justify-center mb-6 shadow-inner"
    >
      <svg
        class="w-10 h-10 text-muted-foreground/40"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path :d="iconPath" />
      </svg>
    </div>

    <!-- Title -->
    <h3 class="text-base font-semibold text-foreground mb-2">
      {{ title }}
    </h3>

    <!-- Description -->
    <p class="text-sm text-muted-foreground max-w-xs mb-6">
      {{ description }}
    </p>

    <!-- Action Button -->
    <slot name="action">
      <button
        v-if="actionText"
        class="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium text-sm transition-all duration-normal ease-out hover:bg-primary/90 hover:shadow-primary-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
        @click="handleAction"
      >
        {{ actionText }}
      </button>
    </slot>
  </div>
</template>
