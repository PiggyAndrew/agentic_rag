<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  status?: 'success' | 'warning' | 'danger' | 'info' | 'default'
  size?: 'sm' | 'md'
  dot?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  status: 'default',
  size: 'md',
  dot: false,
})

const sizeClasses = computed(() => {
  const sizeMap: Record<string, string> = {
    sm: 'text-[10px] px-2 py-0.5',
    md: 'text-xs px-2.5 py-1',
  }
  return sizeMap[props.size] || sizeMap.md
})

const statusClasses = computed(() => {
  const statusMap: Record<string, string> = {
    success: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20',
    warning: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/20',
    danger: 'bg-red-50 text-red-700 border-red-200 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/20',
    info: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-500/10 dark:text-blue-400 dark:border-blue-500/20',
    default: 'bg-gray-100 text-gray-700 border-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-700',
  }
  return statusMap[props.status] || statusMap.default
})

const dotColor = computed(() => {
  const colorMap: Record<string, string> = {
    success: 'bg-emerald-500',
    warning: 'bg-amber-500',
    danger: 'bg-red-500',
    info: 'bg-blue-500',
    default: 'bg-gray-500',
  }
  return colorMap[props.status] || colorMap.default
})
</script>

<template>
  <span
    v-if="dot"
    :class="[
      'relative inline-flex items-center',
      'h-2 w-2 rounded-full',
      dotColor,
    ]"
  >
    <span
      class="absolute inline-flex h-full w-full rounded-full animate-ping opacity-75"
      :class="dotColor"
    />
  </span>
  <span
    v-else
    :class="[
      'inline-flex items-center justify-center font-medium rounded-lg border',
      'transition-all duration-normal ease-out',
      sizeClasses,
      statusClasses,
    ]"
  >
    <slot />
  </span>
</template>
