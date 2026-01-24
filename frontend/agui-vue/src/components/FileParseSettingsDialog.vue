<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, Picture, Operation, Grid, Files } from '@element-plus/icons-vue'

interface Props {
  modelValue: boolean
  file: {
    id: string
    name: string
    type?: string
  } | null
}

const props = defineProps<Props>()
const emit = defineEmits(['update:modelValue', 'save'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

// Form State
const parseMode = ref('text') // 'text' | 'ocr'
const chunkMethod = ref('fixed') // 'fixed' | 'semantic' | 'page'
const chunkSize = ref(500)
const chunkOverlap = ref(50)
const separator = ref('\\n\\n')
const semanticLevel = ref(['h1', 'h2']) // For semantic splitting

// Options
const parseModes = [
  { label: '通用文本解析', value: 'text', icon: Document, desc: '速度快，适用于大多数可复制文字的文档' },
  { label: 'OCR 解析', value: 'ocr', icon: Picture, desc: '速度较慢，适用于扫描件、图片或无法复制文字的 PDF' },
]

const chunkMethods = [
  { label: '固定字符分块', value: 'fixed', icon: Operation, desc: '按字符数截断，简单直接' },
  { label: '按章节/标题分块', value: 'semantic', icon: Grid, desc: '识别文档结构，按段落或标题分割' },
  { label: '按页面分块', value: 'page', icon: Files, desc: '每一页作为一个完整的片段' },
]

// Reset form when file changes or dialog opens
watch(
  () => props.file,
  (newFile) => {
    if (newFile) {
      // Set defaults based on file type
      const isImage = /\.(png|jpg|jpeg|tiff|bmp)$/i.test(newFile.name)
      
      if (isImage) {
        parseMode.value = 'ocr'
      } else {
        parseMode.value = 'text'
      }
      
      chunkMethod.value = 'fixed'
      chunkSize.value = 500
      chunkOverlap.value = 50
    }
  },
  { immediate: true }
)

const handleSave = () => {
  const config = {
    fileId: props.file?.id,
    parseMode: parseMode.value,
    chunkMethod: chunkMethod.value,
    params: {
      chunkSize: chunkSize.value,
      chunkOverlap: chunkOverlap.value,
      separator: separator.value,
      semanticLevel: semanticLevel.value
    }
  }
  emit('save', config)
  visible.value = false
  ElMessage.success('解析配置已保存')
}
</script>

<template>
  <el-dialog
    v-model="visible"
    :title="`解析设置 - ${file?.name || ''}`"
    width="600px"
    destroy-on-close
    class="parse-settings-dialog"
  >
    <div class="space-y-6 py-2">
      <!-- 1. 解析模式 -->
      <div class="space-y-3">
        <div class="text-sm font-medium text-gray-700">1. 解析模式</div>
        <div class="grid grid-cols-2 gap-4">
          <div
            v-for="mode in parseModes"
            :key="mode.value"
            class="relative flex flex-col p-4 border rounded-xl cursor-pointer transition-all hover:border-primary hover:bg-primary/5"
            :class="parseMode === mode.value ? 'border-primary bg-primary/5 ring-1 ring-primary' : 'border-gray-200 bg-white'"
            @click="parseMode = mode.value"
          >
            <div class="flex items-center gap-2 mb-2">
              <el-icon :size="18" :class="parseMode === mode.value ? 'text-primary' : 'text-gray-500'">
                <component :is="mode.icon" />
              </el-icon>
              <span class="font-medium text-sm" :class="parseMode === mode.value ? 'text-primary' : 'text-gray-900'">{{ mode.label }}</span>
            </div>
            <span class="text-xs text-gray-500 leading-relaxed">{{ mode.desc }}</span>
            
            <!-- Checkmark -->
            <div v-if="parseMode === mode.value" class="absolute top-2 right-2 text-primary">
              <div class="w-2 h-2 rounded-full bg-primary"></div>
            </div>
          </div>
        </div>
      </div>

      <el-divider border-style="dashed" />

      <!-- 2. 分块策略 -->
      <div class="space-y-3">
        <div class="text-sm font-medium text-gray-700">2. 分块策略</div>
        <el-radio-group v-model="chunkMethod" class="w-full grid grid-cols-3 gap-3 !flex-nowrap">
          <el-radio-button 
            v-for="method in chunkMethods" 
            :key="method.value" 
            :label="method.value" 
            class="flex-1"
          >
            <div class="flex items-center gap-2 px-1">
              <el-icon><component :is="method.icon" /></el-icon>
              {{ method.label }}
            </div>
          </el-radio-button>
        </el-radio-group>
        
        <div class="bg-gray-50 p-4 rounded-lg text-xs text-gray-500 mt-2">
          {{ chunkMethods.find(m => m.value === chunkMethod)?.desc }}
        </div>
      </div>

      <!-- 3. 参数配置 -->
      <div class="space-y-4 bg-gray-50/50 p-4 rounded-xl border border-gray-100">
        <div class="text-sm font-medium text-gray-700 flex items-center gap-2">
          <span>详细参数</span>
          <el-tag size="small" type="info" effect="plain">{{ chunkMethods.find(m => m.value === chunkMethod)?.label }}</el-tag>
        </div>

        <!-- Fixed Size Params -->
        <template v-if="chunkMethod === 'fixed'">
          <div class="grid grid-cols-2 gap-x-6 gap-y-4">
            <div class="flex flex-col gap-1.5">
              <span class="text-xs text-gray-500">分块大小 (Token/Char)</span>
              <el-input-number v-model="chunkSize" :min="100" :max="4000" :step="100" class="!w-full" controls-position="right" />
            </div>
            <div class="flex flex-col gap-1.5">
              <span class="text-xs text-gray-500">重叠大小 (Overlap)</span>
              <el-input-number v-model="chunkOverlap" :min="0" :max="chunkSize / 2" :step="10" class="!w-full" controls-position="right" />
            </div>
            <div class="col-span-2 flex flex-col gap-1.5">
              <span class="text-xs text-gray-500">分隔符 (Separator)</span>
              <el-input v-model="separator" placeholder="\n\n" />
              <span class="text-[10px] text-gray-400">支持转义字符，如 \n 代表换行</span>
            </div>
          </div>
        </template>

        <!-- Semantic Params -->
        <template v-if="chunkMethod === 'semantic'">
          <div class="space-y-4">
            <div class="flex flex-col gap-2">
              <span class="text-xs text-gray-500">识别标题层级</span>
              <el-checkbox-group v-model="semanticLevel">
                <el-checkbox label="h1">Heading 1</el-checkbox>
                <el-checkbox label="h2">Heading 2</el-checkbox>
                <el-checkbox label="h3">Heading 3</el-checkbox>
              </el-checkbox-group>
            </div>
             <div class="flex flex-col gap-1.5">
              <span class="text-xs text-gray-500">最小分块大小合并阈值</span>
              <el-input-number v-model="chunkSize" :min="50" :max="2000" :step="50" class="!w-full" controls-position="right" />
            </div>
          </div>
        </template>
        
         <!-- Page Params -->
        <template v-if="chunkMethod === 'page'">
          <div class="flex items-center gap-2 text-sm text-gray-600">
            <el-icon class="text-info"><Files /></el-icon>
            <span>将按物理页面进行分割，每页作为一个独立的片段。</span>
          </div>
        </template>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-end gap-3 pt-2">
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存并应用</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
:deep(.el-radio-button__inner) {
  width: 100%;
  display: flex;
  justify-content: center;
  border-radius: 0;
}
:deep(.el-radio-button:first-child .el-radio-button__inner) {
  border-radius: 8px 0 0 8px;
}
:deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-radius: 0 8px 8px 0;
}
</style>
