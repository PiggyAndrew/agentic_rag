<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  variant?: 'default' | 'muted' | 'primary' | 'danger' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  size: 'md',
  disabled: false,
  loading: false,
})

const emit = defineEmits<{
  click: [event: MouseEvent]
}>()

const sizeClasses = computed(() => {
  const sizeMap: Record<string, string> = {
    sm: 'w-8 h-8 text-sm',
    md: 'w-9 h-9',
    lg: 'w-10 h-10 text-lg',
  }
  return sizeMap[props.size] || sizeMap.md
})

const variantClasses = computed(() => {
  const variantMap: Record<string, string> = {
    default: 'text-gray-600 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-800',
    muted: 'text-gray-400 hover:text-gray-600 hover:bg-gray-50 dark:text-gray-500 dark:hover:text-gray-300 dark:hover:bg-gray-800/50',
    primary: 'text-primary hover:text-primary-700 hover:bg-primary/10 dark:text-primary-400 dark:hover:bg-primary/20',
    danger: 'text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:text-red-400 dark:hover:bg-red-500/10',
    ghost: 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200',
  }
  return variantMap[props.variant] || variantMap.default
})

const isDisabled = computed(() => props.disabled || props.loading)

function handleClick(event: MouseEvent) {
  if (!isDisabled.value) {
    emit('click', event)
  }
}
</script>

<template>
  <button
    :class="[
      'inline-flex items-center justify-center rounded-lg transition-all duration-normal ease-out',
      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50',
      'disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none',
      sizeClasses,
      variantClasses,
    ]"
    :disabled="isDisabled"
    @click="handleClick"
  >
    <slot v-if="!loading" />
    <svg
      v-else
      class="animate-spin"
      :class="sizeClasses"
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle
        class="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        stroke-width="4"
      />
      <path
        class="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  </button>
</template>
