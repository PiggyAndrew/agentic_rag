<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { CommandItem } from '@/components/ui/command'

const props = defineProps<{
  value: string
  class?: HTMLAttributes['class']
}>()
</script>

<template>
  <CommandItem :value="props.value" v-bind="$attrs">
    <slot />
  </CommandItem>
</template>
