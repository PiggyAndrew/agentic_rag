<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/lib/utils'

interface Props {
  class?: HTMLAttributes['class']
}

const props = defineProps<Props>()
</script>

<template>
  <div
    :class="
      cn(
        'inline-block w-auto max-w-[90%] md:max-w-[85%] lg:max-w-[80%] overflow-hidden text-sm leading-relaxed text-left',
        'group-[.is-user]:ml-auto group-[.is-user]:rounded-2xl group-[.is-user]:rounded-tr-md group-[.is-user]:bg-primary group-[.is-user]:text-primary-foreground group-[.is-user]:px-5 group-[.is-user]:py-3.5 group-[.is-user]:shadow-md',
        'group-[.is-assistant]:text-gray-800 group-[.is-assistant]:px-1',
        props.class,
      )
    "
    v-bind="$attrs"
  >
    <div class="whitespace-pre-wrap break-words">
      <slot />
    </div>
  </div>
</template>
