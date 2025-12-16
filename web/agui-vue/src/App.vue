<script setup lang="ts">
import KnowledgeBaseChat from '@/components/KnowledgeBaseChat.vue';
</script>

<template>
  <div class="h-screen w-screen bg-background text-foreground">
    <KnowledgeBaseChat />
  </div>
</template>

<style>
/* Remove scoped to ensure body/html styles apply */
html, body, #app {
  height: 100%;
  width: 100%;
  margin: 0;
  padding: 0;
  overflow: hidden;
}
</style>
