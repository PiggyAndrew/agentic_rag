<script setup lang="ts">
import { useConfirmationContext } from './context'

const { state } = useConfirmationContext()
</script>

<template>
  <template v-if="state === 'input-available'">
    <slot />
  </template>
</template>
