<script setup lang="ts">
import { computed, inject } from 'vue'
import {
  InlineCitation,
  InlineCitationCard,
  InlineCitationCardBody,
  InlineCitationCardTrigger,
  InlineCitationCarousel,
  InlineCitationCarouselContent,
  InlineCitationCarouselHeader,
  InlineCitationCarouselIndex,
  InlineCitationCarouselItem,
  InlineCitationCarouselNext,
  InlineCitationCarouselPrev,
  InlineCitationSource,
} from "@/components/ai-elements/inline-citation";

const props = defineProps<{
  dataFileId?: string | number
  dataChunkIndex?: string | number
}>()

// Inject context provided by parent KnowledgeBaseChat
const citationContext = inject<any>('citationContext')

const fileId = computed(() => {
    const val = props.dataFileId
    return val ? Number(val) : NaN
})

const chunkIndex = computed(() => {
    const val = props.dataChunkIndex
    return val ? Number(val) : NaN
})

const isValid = computed(() => Number.isFinite(fileId.value) && Number.isFinite(chunkIndex.value))

const citation = computed(() => {
  if (!citationContext || !isValid.value) return null
  return citationContext.getCitation(fileId.value, chunkIndex.value)
})

const sourceUrl = computed(() => {
    if (!citationContext || !isValid.value) return ''
    const fid = fileId.value
    const kbId = citationContext.selectedKbId.value
    const base = citationContext.apiBase.value
    return kbId
        ? `${base}/api/kb/${encodeURIComponent(kbId)}/files/${encodeURIComponent(`f-${fid}`)}/chunks`
        : `${base}/api/files/${encodeURIComponent(String(fid))}/chunks`
})

const title = computed(() => {
    const c = citation.value
    if (c?.filename) {
        return `${c.filename} · #${c.chunk_index}`
    }
    return `fileId=${fileId.value}, chunkIndex=${chunkIndex.value}`
})

const description = computed(() => {
    const c = citation.value
    return c?.content ? c.content : "悬停或点击加载引用内容"
})

function handleMouseEnter() {
    if (isValid.value && citationContext) {
        citationContext.ensureLoaded(fileId.value, chunkIndex.value)
    }
}

function handleClick(e: MouseEvent) {
    // Stop propagation to prevent message click handlers or other bubbles
    e.preventDefault()
    e.stopPropagation()
    if (isValid.value && citationContext) {
        citationContext.openDialog(fileId.value, chunkIndex.value)
    }
}
</script>

<template>
  <InlineCitation v-if="isValid">
    <InlineCitationCard :open-delay="200" :close-delay="100">
      <InlineCitationCardTrigger
        :sources="[sourceUrl]"
        :label="`[${fileId}:${chunkIndex}]`"
        @mouseenter="handleMouseEnter"
        @click="handleClick"
      />
      <InlineCitationCardBody>
        <InlineCitationCarousel>
          <InlineCitationCarouselHeader>
            <div class="flex items-center gap-2 px-2 py-1 text-xs text-muted-foreground">
              <span>引用</span>
            </div>
            <div class="flex items-center gap-2">
              <InlineCitationCarouselPrev />
              <InlineCitationCarouselNext />
              <InlineCitationCarouselIndex />
            </div>
          </InlineCitationCarouselHeader>
          <InlineCitationCarouselContent>
            <InlineCitationCarouselItem>
              <InlineCitationSource
                :title="title"
                :url="sourceUrl"
                :description="description"
              />
              <div class="mt-2 flex justify-end">
                <button
                  type="button"
                  class="text-xs text-primary hover:underline cursor-pointer"
                  @click="handleClick"
                >
                  查看片段
                </button>
              </div>
            </InlineCitationCarouselItem>
          </InlineCitationCarouselContent>
        </InlineCitationCarousel>
      </InlineCitationCardBody>
    </InlineCitationCard>
  </InlineCitation>
</template>
