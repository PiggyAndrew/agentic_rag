<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  padding?: 'none' | 'sm' | 'md' | 'lg' | 'xl'
  shadow?: 'none' | 'sm' | 'md' | 'lg' | 'xl' | 'primary'
  hover?: boolean
  clickable?: boolean
  bordered?: boolean
  variant?: 'default' | 'muted' | 'primary' | 'danger'
}

const props = withDefaults(defineProps<Props>(), {
  padding: 'lg',
  shadow: 'sm',
  hover: false,
  clickable: false,
  bordered: true,
  variant: 'default',
})

const emit = defineEmits<{
  click: [event: MouseEvent]
}>()

const paddingClass = computed(() => {
  const paddingMap: Record<string, string> = {
    none: '',
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-5',
    xl: 'p-6',
  }
  return paddingMap[props.padding] || paddingMap.lg
})

const shadowClass = computed(() => {
  const shadowMap: Record<string, string> = {
    none: 'shadow-none',
    sm: 'shadow-sm',
    md: 'shadow-md',
    lg: 'shadow-lg',
    xl: 'shadow-xl',
    primary: 'shadow-primary-sm',
  }
  return shadowMap[props.shadow] || shadowMap.sm
})

const variantClasses = computed(() => {
  const variantMap: Record<string, string> = {
    default: 'bg-card border-border',
    muted: 'bg-muted/50 border-muted',
    primary: 'bg-primary/5 border-primary/20',
    danger: 'bg-destructive/5 border-destructive/20',
  }
  return variantMap[props.variant] || variantMap.default
})

const cursorClass = computed(() => {
  if (props.clickable) return 'cursor-pointer'
  return ''
})

const hoverClasses = computed(() => {
  if (!props.hover) return ''
  return 'transition-all duration-normal ease-out hover:shadow-md hover:border-primary/30'
})

function handleClick(event: MouseEvent) {
  if (props.clickable) {
    emit('click', event)
  }
}
</script>

<template>
  <div
    :class="[
      'rounded-xl border transition-all',
      variantClasses,
      bordered ? 'border' : 'border-0',
      paddingClass,
      shadowClass,
      cursorClass,
      hoverClasses,
    ]"
    @click="handleClick"
  >
    <slot />
  </div>
</template>
