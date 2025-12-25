<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Edit, Upload as UploadIcon, Document, FolderOpened} from '@element-plus/icons-vue'
import { useKbStore } from '@/stores/kb'
import ChunkViewerDialog from '@/components/ChunkViewerDialog.vue'

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
}

const kbStore = useKbStore()
const knowledgeBases = computed<KnowledgeBase[]>(() => kbStore.knowledgeBases)
const selectedKbId = computed<string>({
  get: () => kbStore.selectedKbId,
  set: (v) => (kbStore.selectedKbId = v),
})
const files = computed<FileItem[]>(() => kbStore.filesByKb[selectedKbId.value] || [])
const fileSearch = ref<string>('')
const isCreatingKb = ref<boolean>(false)
const newKbName = ref<string>('')
const newKbDesc = ref<string>('')
const showChunkModal = ref<boolean>(false)
const chunks = ref<any[]>([])
const parsingFileIds = ref<Set<string>>(new Set())

/**
 * 加载知识库列表（后端）
 */
function loadKnowledgeBases(): void {
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
  parsingFileIds.value.add(file.id)
  try {
    await kbStore.vectorizeFile(selectedKbId.value, file.name)
    ElMessage.success('向量化完成')
    await kbStore.fetchFiles(selectedKbId.value)
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
</script>

<template>
  <el-container class="h-full w-full bg-background">
    <!-- 侧边栏 -->
    <el-aside width="280px" class="flex flex-col border-r bg-card">
      <div class="h-14 px-4 flex items-center justify-between border-b shrink-0">
        <div class="flex items-center gap-2 text-sm font-medium text-foreground">
          <el-icon class="text-primary"><FolderOpened /></el-icon>
          <span>知识库列表</span>
        </div>
        <el-button type="primary" link :icon="Plus" @click="isCreatingKb = true">
          新建
        </el-button>
      </div>
      
      <div class="flex-1 overflow-hidden min-h-0">
        <el-scrollbar height="100%">
          <div class="p-2">
            <template v-if="knowledgeBases.length > 0">
              <div
                v-for="kb in knowledgeBases"
                :key="kb.id"
                class="group flex items-center justify-between p-3 mb-1 rounded-md cursor-pointer transition-all duration-200 border-l-4"
                :class="selectedKbId === kb.id 
                  ? 'bg-primary/10 border-primary text-primary shadow-sm' 
                  : 'border-transparent hover:bg-accent hover:text-accent-foreground text-foreground'"
                @click="selectKnowledgeBase(kb.id)"
              >
                <div class="flex flex-col overflow-hidden">
                  <span class="font-medium truncate">{{ kb.name }}</span>
                  <span v-if="kb.description" class="text-xs text-muted-foreground truncate mt-0.5">{{ kb.description }}</span>
                </div>
                <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity" :class="{ 'opacity-100': selectedKbId === kb.id }">
                  <el-button link size="small" :icon="Edit" @click.stop="renameKnowledgeBase(kb.id)" />
                  <el-button link size="small" type="danger" :icon="Delete" @click.stop="deleteKnowledgeBase(kb.id)" />
                </div>
              </div>
            </template>
            <div v-else class="text-center py-8 text-muted-foreground text-sm">
              暂无知识库
            </div>
          </div>
        </el-scrollbar>
      </div>
    </el-aside>
    <!-- 主内容区 -->
    <el-container class="flex flex-col h-full overflow-hidden bg-background min-w-0">
      <el-header height="64px" class="flex items-center justify-between px-6 border-b bg-card shrink-0 shadow-sm z-10">
        <div class="flex items-center gap-3 overflow-hidden">
          <div class="p-2 rounded-lg bg-primary/10 text-primary">
            <el-icon size="20"><Document /></el-icon>
          </div>
          <div class="flex flex-col">
            <span class="text-base font-semibold text-foreground truncate max-w-[200px]">{{ currentKb?.name || '未选择知识库' }}</span>
            <span class="text-xs text-muted-foreground" v-if="currentKb">共 {{ filteredFiles.length }} 个文件</span>
          </div>
        </div>
        
        <div class="flex items-center gap-3" v-if="currentKb">
          <el-input
            v-model="fileSearch"
            placeholder="搜索文件..."
            size="default"
            class="w-64"
            clearable
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-upload
            multiple
            :show-file-list="false"
            :auto-upload="false"
            :on-change="onUploadChange"
            accept=".pdf,.xlsx"
          >
            <el-button type="primary" :icon="UploadIcon">添加文件</el-button>
          </el-upload>
        </div>
      </el-header>

      <el-main class="flex-1 overflow-hidden p-0 relative">
        <div v-if="!selectedKbId" class="absolute inset-0 flex flex-col items-center justify-center text-muted-foreground">
          <el-icon size="48" class="mb-4 opacity-20"><FolderOpened /></el-icon>
          <p>请选择或新建一个知识库</p>
        </div>
        
        <el-table
          v-else
          :data="filteredFiles"
          style="width: 100%; height: 100%"
          :header-cell-style="{ background: 'transparent' }"
        >
          <template #empty>
            <div class="py-8 flex flex-col items-center text-muted-foreground">
              <el-icon size="40" class="mb-2 opacity-20"><Document /></el-icon>
              <span>暂无文件，请上传 PDF 或 Excel</span>
            </div>
          </template>
          
          <el-table-column prop="name" label="文件名" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <div class="flex items-center gap-2">
                <el-icon :class="row.name.endsWith('.pdf') ? 'text-red-500' : 'text-green-600'">
                  <Document />
                </el-icon>
                <span>{{ row.name }}</span>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column prop="type" label="类型" width="120">
            <template #default="{ row }">
              <el-tag size="small" variant="plain" class="uppercase">
                {{ row.name.split('.').pop() }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="chunkCount" label="片段数" width="100" align="center">
            <template #default="{ row }">
              <span class="font-mono text-xs bg-muted px-2 py-0.5 rounded-full">{{ row.chunkCount }}</span>
            </template>
          </el-table-column>
          
          <el-table-column prop="createdAt" label="上传时间" width="180">
            <template #default="{ row }">
              <span class="text-xs text-muted-foreground">{{ new Date(row.createdAt).toLocaleString() }}</span>
            </template>
          </el-table-column>
          
          <el-table-column label="操作" width="260" fixed="right">
            <template #default="{ row }">
              <el-button size="small" plain @click="viewChunks(row.id)">查看</el-button>
              <el-button 
                type="primary" 
                size="small" 
                plain 
                @click="vectorizeFile(row)"
                :loading="parsingFileIds.has(row.id)"
                :disabled="parsingFileIds.has(row.id)"
              >
                {{ parsingFileIds.has(row.id) ? '解析中...' : (row.chunkCount > 0 ? '重新解析' : '解析') }}
              </el-button>
              <el-button type="danger" size="small" plain text @click="removeFile(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-main>
    </el-container>
  </el-container>

  <el-dialog v-model="isCreatingKb" title="新建知识库" width="520px">
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
</template>

<style scoped>
.border-r { border-right: 1px solid var(--el-border-color); }
.border-b { border-bottom: 1px solid var(--el-border-color); }
</style>
