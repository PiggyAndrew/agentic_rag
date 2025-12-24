<script setup lang="ts">
import { useConfirmationContext } from './context'

const { approval, state } = useConfirmationContext()
</script>

<template>
  <template
    v-if="approval?.approved === false && state === 'output-error'"
  >
    <slot />
  </template>
</template>
