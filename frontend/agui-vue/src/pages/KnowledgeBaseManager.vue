<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Edit, Upload as UploadIcon, Document, FolderOpened, Setting } from '@element-plus/icons-vue'
import { useKbStore } from '@/stores/kb'
import ChunkViewerDialog from '@/components/ChunkViewerDialog.vue'
import FileParseSettingsDialog from '@/components/FileParseSettingsDialog.vue'

interface KnowledgeBase {
  id: string
  name: string
  description?: string
  createdAt?: number
}

interface FileItem {
  id: string
  name: string
  type: string
  kbId: string
  createdAt: number
  chunkCount: number
  status: string
}

const kbStore = useKbStore()
const knowledgeBases = computed<KnowledgeBase[]>(() => {
  const list = kbStore.knowledgeBases as any
  return Array.isArray(list) ? list : []
})
const selectedKbId = computed<string>({
  get: () => kbStore.selectedKbId,
  set: (v) => (kbStore.selectedKbId = v), 
})
const files = computed<FileItem[]>(() => {
  const raw = kbStore.filesByKb[selectedKbId.value] as any
  return Array.isArray(raw) ? raw : []
})
const fileSearch = ref<string>('')
const isCreatingKb = ref<boolean>(false)
const newKbName = ref<string>('')
const newKbDesc = ref<string>('')
const showChunkModal = ref<boolean>(false)
const chunks = ref<any[]>([])
const parsingFileIds = ref<Set<string>>(new Set())

// Parsing Settings State
const showSettingsDialog = ref(false)
const currentSettingsFile = ref<FileItem | null>(null)

/**
 * 将后端文件状态映射为中文文案与样式
 */
function statusMeta(status: string): { text: string; type: 'info' | 'success' | 'warning' | 'danger' } {
  const s = (status || '').toLowerCase()
  if (s === 'uploaded') return { text: '未分割', type: 'warning' }
  if (s === 'chunked') return { text: '已分割', type: 'info' }
  if (s === 'vectorized' || s === 'done') return { text: '已向量化', type: 'success' }
  return { text: '未知', type: 'danger' }
}

/**
 * 加载知识库列表（后端）
 */
function loadKnowledgeBases(): void {
  console.log('loadKnowledgeBases')
  kbStore.fetchKnowledgeBases().then(() => {
    if (kbStore.selectedKbId) {
      loadFiles(kbStore.selectedKbId)
    }
  })
}

/**
 * 选择知识库并加载其文件（后端）
 */
function selectKnowledgeBase(id: string): void {
  console.log('selectKnowledgeBase', id)
  selectedKbId.value = id
  loadFiles(id)
}

/**
 * 加载文件列表（后端）
 */
function loadFiles(kbId: string): void {
  kbStore.fetchFiles(kbId)
}

/**
 * 创建知识库（后端）
 */
async function createKnowledgeBase(): Promise<void> {
  if (!newKbName.value.trim()) {
    ElMessage.warning('请输入知识库名称')
    return
  }
  await kbStore.createKnowledgeBase(newKbName.value.trim(), newKbDesc.value.trim())
  newKbName.value = ''
  newKbDesc.value = ''
  isCreatingKb.value = false
  ElMessage.success('知识库创建成功')
}

/**
 * 删除知识库（后端）
 */
async function deleteKnowledgeBase(kbId: string): Promise<void> {
  const kb = knowledgeBases.value.find(k => k.id === kbId)
  if (!kb) return
  await ElMessageBox.confirm(`确定删除知识库「${kb.name}」？该操作不可恢复。`, '删除确认', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
  await kbStore.deleteKnowledgeBase(kbId)
  ElMessage.success('知识库已删除')
}

/**
 * 重命名知识库（后端）
 */
async function renameKnowledgeBase(kbId: string): Promise<void> {
  const kb = knowledgeBases.value.find(k => k.id === kbId)
  if (!kb) return
  const { value } = await ElMessageBox.prompt('输入新的知识库名称', '重命名', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    inputValue: kb.name,
    inputPlaceholder: '新的知识库名称',
  })
  await kbStore.updateKnowledgeBase(kbId, value.trim(), kb.description)
  ElMessage.success('知识库名称已更新')
}

/**
 * 上传文件（后端）
 */
async function handleFileUpload(fileList: File[]): Promise<void> {
  if (!selectedKbId.value) {
    ElMessage.warning('请先选择知识库')
    return
  }
  for (const f of fileList) {
    if (!['application/pdf', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'].includes(f.type)) {
      ElMessage.error('仅支持上传 PDF 或 Excel(xlsx) 文件')
      continue
    }
    await kbStore.uploadFile(selectedKbId.value, f)
  }
  await kbStore.fetchFiles(selectedKbId.value)
  ElMessage.success('文件已添加（上传完成）')
}

/**
 * 查看片段（后端）
 */
async function viewChunks(fileId: string): Promise<void> {
  if (!selectedKbId.value) return
  const data = await kbStore.fetchChunks(selectedKbId.value, fileId)
  chunks.value = data
  showChunkModal.value = true
}

/**
 * 触发向量化（后端）
 */
async function vectorizeFile(file: FileItem): Promise<void> {
  if (!selectedKbId.value) return
  kbStore.patchFileLocal(selectedKbId.value, file.id, { status: 'uploaded', chunkCount: 0 })
  parsingFileIds.value.add(file.id)
  try {
    await kbStore.vectorizeFile(selectedKbId.value, file.name)
    ElMessage.success('向量化完成')
    await kbStore.fetchFiles(selectedKbId.value)
  } catch (e) {
    await kbStore.fetchFiles(selectedKbId.value)
    throw e
  } finally {
    parsingFileIds.value.delete(file.id)
  }
}

/**
 * 删除文件（后端）
 */
async function removeFile(fileId: string): Promise<void> {
  const file = files.value.find(f => f.id === fileId)
  if (!file) return

  await ElMessageBox.confirm(
    `确定要删除文件「${file.name}」吗？\n删除后该文件及其所有片段将无法恢复。`, 
    '删除确认', 
    {
      type: 'warning',
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--danger'
    }
  )

  await kbStore.deleteFile(fileId, selectedKbId.value)
  ElMessage.success('文件已删除')
}

const currentKb = computed(() => knowledgeBases.value.find(k => k.id === selectedKbId.value))
const filteredFiles = computed(() => {
  const q = fileSearch.value.trim().toLowerCase()
  if (!q) return files.value
  return files.value.filter(f => f.name.toLowerCase().includes(q))
})

onMounted(() => {
  loadKnowledgeBases()
})

/**
 * 处理上传组件的文件变更事件
 */
function onUploadChange(file: any): void {
  if (file?.raw) {
    handleFileUpload([file.raw as File])
  }
}

/**
 * 打开解析设置弹窗
 */
function openSettings(file: FileItem) {
  currentSettingsFile.value = file
  showSettingsDialog.value = true
}

/**
 * 保存解析设置（暂无后端接口，仅打印）
 */
function handleSaveSettings(config: any) {
  console.log('保存解析配置:', config)
  // TODO: 调用后端 API 保存配置，例如 await kbStore.updateFileSettings(config)
  // 如果需要立即生效，也可以在这里触发重新解析
}
</script>

<template>
  <el-container class="h-full w-full bg-background">
    <!-- 侧边栏 -->
    <el-aside width="300px" class="flex flex-col border-r border-border bg-muted/30 backdrop-blur-sm">
      <div class="h-16 px-5 flex items-center justify-between border-b border-border bg-card/50 shrink-0">
        <div class="flex items-center gap-2.5">
          <div class="p-1.5 rounded-lg bg-primary/10 text-primary">
             <el-icon :size="18"><FolderOpened /></el-icon>
          </div>
          <span class="text-sm font-semibold text-foreground">知识库管理</span>
        </div>
        <el-tooltip content="新建知识库" placement="bottom">
          <el-button type="primary" circle size="small" :icon="Plus" @click="isCreatingKb = true" class="shadow-sm shadow-primary/20 transition-all duration-normal ease-out hover:shadow-md hover:scale-105" />
        </el-tooltip>
      </div>

      <div class="flex-1 overflow-hidden min-h-0 p-3">
        <el-scrollbar height="100%">
          <div class="space-y-1.5">
            <template v-if="knowledgeBases.length > 0">
              <div
                v-for="kb in knowledgeBases"
                :key="kb.id"
                class="group relative flex items-center justify-between p-3.5 rounded-xl cursor-pointer transition-all duration-normal ease-out border"
                :class="selectedKbId === kb.id
                  ? 'bg-card border-primary/30 shadow-sm ring-1 ring-primary/10 z-10'
                  : 'bg-transparent border-transparent hover:bg-card hover:border-border hover:shadow-sm text-muted-foreground hover:text-foreground'"
                @click="selectKnowledgeBase(kb.id)"
              >
                <!-- 选中指示条 -->
                <div
                  v-if="selectedKbId === kb.id"
                  class="absolute left-0 top-1/2 -translate-y-1/2 h-8 w-1 bg-primary rounded-r-full"
                ></div>

                <div class="flex flex-col overflow-hidden pl-2 min-w-0">
                  <span class="font-medium text-sm truncate" :class="selectedKbId === kb.id ? 'text-primary' : ''">{{ kb.name }}</span>
                  <span v-if="kb.description" class="text-xs text-muted-foreground truncate mt-0.5">{{ kb.description }}</span>
                </div>

                <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all duration-normal ease-out translate-x-2 group-hover:translate-x-0" :class="{ 'opacity-100': selectedKbId === kb.id }">
                  <el-button link size="small" :icon="Edit" @click.stop="renameKnowledgeBase(kb.id)" class="!text-muted-foreground hover:!text-primary transition-colors" />
                  <el-button link size="small" :icon="Delete" @click.stop="deleteKnowledgeBase(kb.id)" class="!text-muted-foreground hover:!text-destructive transition-colors" />
                </div>
              </div>
            </template>
            <div v-else class="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <div class="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center mb-4 shadow-inner">
                <el-icon size="32" class="opacity-20"><FolderOpened /></el-icon>
              </div>
              <span class="text-sm font-medium">暂无知识库</span>
              <el-button type="primary" link class="mt-2" @click="isCreatingKb = true">立即创建</el-button>
            </div>
          </div>
        </el-scrollbar>
      </div>
    </el-aside>

    <!-- 主内容区 -->
    <el-container class="flex flex-col h-full overflow-hidden bg-background min-w-0">
      <el-header height="auto" class="flex items-center justify-between px-8 py-5 border-b border-border bg-card shrink-0 z-[var(--z-sticky)]">
        <div class="flex items-center gap-4 overflow-hidden">
          <div class="p-3 rounded-xl bg-gradient-to-br from-primary/10 to-primary/5 text-primary shadow-inner">
            <el-icon size="24"><Document /></el-icon>
          </div>
          <div class="flex flex-col gap-0.5 min-w-0">
            <span class="text-lg font-bold text-foreground truncate">{{ currentKb?.name || '未选择知识库' }}</span>
            <div class="flex items-center gap-2 text-xs text-muted-foreground" v-if="currentKb">
              <span class="bg-muted px-2 py-0.5 rounded-full">{{ filteredFiles.length }} 个文件</span>
              <span v-if="currentKb.description" class="truncate max-w-[400px] border-l border-border pl-2">{{ currentKb.description }}</span>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-3" v-if="currentKb">
          <el-input
            v-model="fileSearch"
            placeholder="搜索文件名..."
            size="default"
            class="w-64 !rounded-lg"
            clearable
          >
            <template #prefix>
              <el-icon class="text-muted-foreground"><Search /></el-icon>
            </template>
          </el-input>
          <el-upload
            multiple
            :show-file-list="false"
            :auto-upload="false"
            :on-change="onUploadChange"
            accept=".pdf,.xlsx"
          >
            <el-button type="primary" :icon="UploadIcon" class="shadow-sm shadow-primary/20 transition-all duration-normal ease-out hover:shadow-md">添加文件</el-button>
          </el-upload>
        </div>
      </el-header>

      <el-main class="flex-1 overflow-hidden p-0 relative bg-muted/20">
        <div v-if="!selectedKbId" class="absolute inset-0 flex flex-col items-center justify-center text-muted-foreground bg-muted/30">
          <div class="w-24 h-24 rounded-full bg-muted flex items-center justify-center mb-6 shadow-inner">
            <el-icon size="40" class="opacity-20"><FolderOpened /></el-icon>
          </div>
          <p class="text-base font-medium text-foreground mb-1">请选择或新建一个知识库</p>
          <p class="text-xs">在左侧列表选择已有知识库，或点击"新建"按钮</p>
        </div>

        <div v-else class="h-full p-6">
          <div class="h-full bg-card rounded-xl border border-border shadow-sm overflow-hidden">
            <el-table
              :data="filteredFiles"
              style="width: 100%; height: 100%"
              :header-cell-style="{ background: 'var(--color-muted)', color: 'var(--color-muted-foreground)', fontWeight: '600', height: '48px' }"
              :row-style="{ height: '60px' }"
            >
              <template #empty>
                <div class="py-16 flex flex-col items-center text-muted-foreground">
                  <div class="w-20 h-20 rounded-full bg-muted flex items-center justify-center mb-4">
                    <el-icon size="32" class="opacity-20"><Document /></el-icon>
                  </div>
                  <span class="text-sm font-medium text-foreground">暂无文件</span>
                  <span class="text-xs mt-1">点击右上角"添加文件"上传 PDF 或 Excel</span>
                </div>
              </template>

              <el-table-column prop="name" label="文件名" min-width="240" show-overflow-tooltip>
                <template #default="{ row }">
                  <div class="flex items-center gap-3 group">
                    <div class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-colors"
                      :class="row.name.endsWith('.pdf') ? 'bg-red-50 text-red-500' : 'bg-emerald-50 text-emerald-600'">
                      <el-icon :size="18">
                        <Document />
                      </el-icon>
                    </div>
                    <div class="flex flex-col min-w-0">
                      <span class="text-sm font-medium text-foreground group-hover:text-primary transition-colors truncate">{{ row.name }}</span>
                      <span class="text-[10px] text-muted-foreground uppercase tracking-wider">{{ row.name.split('.').pop() }}</span>
                    </div>
                  </div>
                </template>
              </el-table-column>

              <el-table-column prop="status" label="状态" width="140">
                <template #default="{ row }">
                  <div class="flex items-center gap-2">
                    <span class="relative flex h-2 w-2">
                      <span class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
                        :class="statusMeta(row.status).type === 'success' ? 'bg-emerald-400' : (statusMeta(row.status).type === 'warning' ? 'bg-amber-400' : 'bg-gray-400')"></span>
                      <span class="relative inline-flex rounded-full h-2 w-2"
                        :class="statusMeta(row.status).type === 'success' ? 'bg-emerald-500' : (statusMeta(row.status).type === 'warning' ? 'bg-amber-500' : 'bg-gray-500')"></span>
                    </span>
                    <span class="text-xs font-medium"
                      :class="statusMeta(row.status).type === 'success' ? 'text-emerald-600' : (statusMeta(row.status).type === 'warning' ? 'text-amber-600' : 'text-muted-foreground')">
                      {{ statusMeta(row.status).text }}
                    </span>
                  </div>
                </template>
              </el-table-column>

              <el-table-column prop="chunkCount" label="片段数" width="120" align="center">
                <template #default="{ row }">
                  <span class="inline-flex items-center justify-center min-w-[32px] px-2 py-1 text-xs font-mono font-medium rounded-lg bg-muted text-foreground">
                    {{ row.chunkCount }}
                  </span>
                </template>
              </el-table-column>

              <el-table-column prop="createdAt" label="上传时间" width="180">
                <template #default="{ row }">
                  <span class="text-xs text-muted-foreground font-mono">{{ new Date(row.createdAt).toLocaleString() }}</span>
                </template>
              </el-table-column>

              <el-table-column label="操作" width="220" fixed="right" align="right">
                <template #default="{ row }">
                  <div class="flex items-center justify-end gap-2 pr-4 opacity-80 hover:opacity-100 transition-opacity">
                    <el-button size="small" :icon="Setting" circle @click="openSettings(row)" class="!mr-1 !rounded-lg" title="解析设置" />
                    <el-button size="small" @click="viewChunks(row.id)" class="!rounded-lg">查看</el-button>
                    <el-button
                      type="primary"
                      size="small"
                      plain
                      @click="vectorizeFile(row)"
                      :loading="parsingFileIds.has(row.id)"
                      :disabled="parsingFileIds.has(row.id)"
                      class="!rounded-lg"
                    >
                      {{
                        parsingFileIds.has(row.id)
                          ? '解析中'
                          : (row.status === 'uploaded'
                              ? '解析'
                              : (row.status === 'chunked'
                                  ? '向量化'
                                  : '重试'))
                      }}
                    </el-button>
                    <el-popconfirm
                      title="确定删除该文件吗？"
                      confirm-button-text="删除"
                      cancel-button-text="取消"
                      confirm-button-type="danger"
                      width="200"
                      @confirm="removeFile(row.id)"
                    >
                      <template #reference>
                        <el-button type="danger" size="small" link :icon="Delete" class="!ml-0" />
                      </template>
                    </el-popconfirm>
                  </div>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </el-main>
    </el-container>
  </el-container>

  <el-dialog v-model="isCreatingKb" title="新建知识库" width="520px" class="!rounded-xl">
    <div class="space-y-4">
      <el-input v-model="newKbName" placeholder="知识库名称" />
      <el-input v-model="newKbDesc" type="textarea" placeholder="描述（可选）" />
    </div>
    <template #footer>
      <div class="flex justify-end gap-2">
        <el-button @click="isCreatingKb = false">取消</el-button>
        <el-button type="primary" @click="createKnowledgeBase">创建</el-button>
      </div>
    </template>
  </el-dialog>

  <ChunkViewerDialog v-model="showChunkModal" :chunks="chunks" />

  <FileParseSettingsDialog
    v-model="showSettingsDialog"
    :file="currentSettingsFile"
    @save="handleSaveSettings"
  />
</template>

<style scoped>
/* Layout overrides */
.border-r { border-right: 1px solid var(--color-border); }
.border-b { border-bottom: 1px solid var(--color-border); }

/* Custom scrollbar for better UX */
:deep(.el-scrollbar__wrap) {
  overflow-x: hidden;
}

:deep(.el-scrollbar__bar.is-vertical > div) {
  background-color: rgb(156 163 175 / 0.3);
}

:deep(.el-scrollbar__bar.is-horizontal > div) {
  background-color: rgb(156 163 175 / 0.3);
}
</style>
