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
  dataCites?: string
}>()

// Inject context provided by parent KnowledgeBaseChat
const citationContext = inject<any>('citationContext')

type CitationRef = { fileId: number; chunkIndex: number; lineRanges?: Array<[number, number]> }

function parseCites(raw: string | undefined): CitationRef[] {
  const s = String(raw ?? '').trim()
  if (!s) return []
  try {
    const json = JSON.parse(s)
    if (Array.isArray(json)) {
      return json
        .map((x) => {
          const fileId = Number((x as any)?.fileId)
          const chunkIndex = Number((x as any)?.chunkIndex)
          const lineRanges = Array.isArray((x as any)?.lineRanges) ? (x as any).lineRanges : undefined
          if (!Number.isFinite(fileId) || !Number.isFinite(chunkIndex)) return null
          return { fileId, chunkIndex, ...(lineRanges ? { lineRanges } : {}) } as CitationRef
        })
        .filter(Boolean) as CitationRef[]
    }
  } catch {
  }
  return []
}

const fallbackRef = computed<CitationRef | null>(() => {
  const fid = props.dataFileId != null ? Number(props.dataFileId) : NaN
  const cidx = props.dataChunkIndex != null ? Number(props.dataChunkIndex) : NaN
  if (!Number.isFinite(fid) || !Number.isFinite(cidx)) return null
  return { fileId: fid, chunkIndex: cidx }
})

const citeRefs = computed<CitationRef[]>(() => {
  const parsed = parseCites(props.dataCites)
  if (parsed.length > 0) return parsed
  return fallbackRef.value ? [fallbackRef.value] : []
})

const isValid = computed(() => citeRefs.value.length > 0)

const sourceUrls = computed(() => {
  if (!citationContext || !isValid.value) return []
  const kbId = citationContext.selectedKbId.value
  const base = citationContext.getApiBase ? citationContext.getApiBase() : ''
  return citeRefs.value.map((r) => {
    const fid = r.fileId
    return kbId
      ? `${base}/api/kb/${encodeURIComponent(kbId)}/files/${encodeURIComponent(`f-${fid}`)}/chunks`
      : `${base}/api/files/${encodeURIComponent(String(fid))}/chunks`
  })
})

const label = computed(() => {
  if (!isValid.value) return ''
  if (citeRefs.value.length === 1) {
    const r = citeRefs.value[0]
    if (!r) return ''
    return `[${r.fileId}:${r.chunkIndex}]`
  }
  return `引用×${citeRefs.value.length}`
})

function formatLineRanges(ranges?: Array<[number, number]>): string {
  if (!ranges || ranges.length === 0) return ''
  return ranges
    .map(([a, b]) => (a === b ? `L${a}` : `L${a}-${b}`))
    .join('，')
}

const citeItems = computed(() => {
  if (!citationContext || !isValid.value) return []
  return citeRefs.value.map((ref) => {
    const c = citationContext.getCitation(ref.fileId, ref.chunkIndex)
    const title = c?.filename ? `${c.filename} · #${c.chunk_index}` : `fileId=${ref.fileId}, chunkIndex=${ref.chunkIndex}`
    const lineText = formatLineRanges(ref.lineRanges)
    const content = c?.content ? String(c.content) : '悬停或点击加载引用内容'
    const description = lineText ? `${lineText}\n${content}` : content
    return { ref, title, description }
  })
})

function handleMouseEnter() {
  if (isValid.value && citationContext) {
    for (const r of citeRefs.value) {
      citationContext.ensureLoaded(r.fileId, r.chunkIndex)
    }
  }
}

function handleClick(e: MouseEvent) {
    // Stop propagation to prevent message click handlers or other bubbles
    e.preventDefault()
    e.stopPropagation()
  if (isValid.value && citationContext) {
    citationContext.openDialog(citeRefs.value)
  }
}
</script>

<template>
  <InlineCitation v-if="isValid">
    <InlineCitationCard :open-delay="200" :close-delay="100">
      <InlineCitationCardTrigger
        :sources="sourceUrls"
        :label="label"
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
            <InlineCitationCarouselItem v-for="(item, idx) in citeItems" :key="idx">
              <InlineCitationSource
                :title="item.title"
                :url="sourceUrls[idx] || ''"
                :description="item.description"
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
