<!-- StatusBadge.vue -->
<script setup lang="ts">
import type { ToolUIPart } from 'ai'
import type { Component } from 'vue'
import { Badge } from '@/components/ui/badge'
import {
  CheckCircleIcon,
  CircleIcon,
  ClockIcon,
  XCircleIcon,
} from 'lucide-vue-next'
import { computed } from 'vue'

const props = defineProps<{
  state: ToolUIPart['state']
}>()

const label = computed(() => {
  const labels: Record<ToolUIPart['state'], string> = {
    'input-streaming': 'Pending',
    'input-available': 'Running',
    'output-available': 'Completed',
    'output-error': 'Error',
  }
  return labels[props.state]
})

const icon = computed<Component>(() => {
  const icons: Record<ToolUIPart['state'], Component> = {
    'input-streaming': CircleIcon,
    'input-available': ClockIcon,
    'output-available': CheckCircleIcon,
    'output-error': XCircleIcon,
  }
  return icons[props.state]
})

const iconClass = computed(() => {
  const classes: Record<string, boolean> = {
    'size-4': true,
    'animate-pulse': props.state === 'input-available',
    'text-green-600': props.state === 'output-available',
    'text-red-600': props.state === 'output-error',
  }
  return classes
})
</script>

<template>
  <Badge class="gap-1.5 rounded-full text-xs" variant="secondary">
    <component :is="icon" :class="iconClass" />
    <span>{{ label }}</span>
  </Badge>
</template>
