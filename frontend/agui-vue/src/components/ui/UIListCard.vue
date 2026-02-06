<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  active?: boolean
  clickable?: boolean
  hover?: boolean
  size?: 'sm' | 'md' | 'lg'
}

const props = withDefaults(defineProps<Props>(), {
  active: false,
  clickable: true,
  hover: true,
  size: 'md',
})

const emit = defineEmits<{
  click: [event: MouseEvent]
}>()

const sizeClasses = computed(() => {
  const sizeMap: Record<string, string> = {
    sm: 'px-3 py-2',
    md: 'px-4 py-3.5',
    lg: 'px-5 py-4',
  }
  return sizeMap[props.size] || sizeMap.md
})

const activeClasses = computed(() => {
  if (props.active) {
    return 'bg-card border-primary/30 shadow-md ring-1 ring-primary/10 z-10'
  }
  return 'bg-transparent border-transparent hover:bg-card hover:border-border hover:shadow-sm'
})

const cursorClass = computed(() => {
  if (props.clickable) return 'cursor-pointer'
  return ''
})

const transitionClasses = computed(() => {
  if (props.hover || props.clickable) {
    return 'transition-all duration-normal ease-out'
  }
  return ''
})

// const activeIndicator = computed(() => {
//   if (!props.active) return null
//   return (
//     <div class="absolute left-0 top-1/2 -translate-y-1/2 h-8 w-1 bg-primary rounded-r-full" />
//   )
// })

function handleClick(event: MouseEvent) {
  if (props.clickable) {
    emit('click', event)
  }
}
</script>

<template>
  <div
    :class="[
      'group relative flex items-center gap-3 rounded-xl border',
      sizeClasses,
      activeClasses,
      cursorClass,
      transitionClasses,
    ]"
    @click="handleClick"
  >
    <template v-if="active">
      <div class="absolute left-0 top-1/2 -translate-y-1/2 h-8 w-1 bg-primary rounded-r-full" />
    </template>

    <div class="flex flex-col overflow-hidden min-w-0 pl-2">
      <slot />
    </div>

    <!-- Action buttons slot (visible on hover when not active, always visible when active) -->
    <div
      v-if="$slots.actions"
      :class="[
        'flex items-center gap-1 shrink-0',
        'transition-all duration-normal ease-out',
        'opacity-0 group-hover:opacity-100 translate-x-2 group-hover:translate-x-0',
        { 'opacity-100': active }
      ]"
    >
      <slot name="actions" />
    </div>
  </div>
</template>
