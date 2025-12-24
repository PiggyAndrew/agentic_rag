<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Edit, Upload as UploadIcon, Document, FolderOpened } from '@element-plus/icons-vue'
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
async function vectorizeFile(filename: string): Promise<void> {
  if (!selectedKbId.value) return
  await kbStore.vectorizeFile(selectedKbId.value, filename)
  ElMessage.success('向量化完成')
  await kbStore.fetchFiles(selectedKbId.value)
}

/**
 * 删除文件（后端）
 */
async function removeFile(fileId: string): Promise<void> {
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
  <el-container class="h-screen w-screen">
    <el-aside width="280px" class="border-r">
      <div class="p-3 flex items-center justify-between">
        <div class="flex items-center gap-2 text-sm text-muted-foreground">
          <el-icon><FolderOpened /></el-icon>
          <span>知识库</span>
        </div>
        <el-button type="primary" size="small" :icon="Plus" @click="isCreatingKb = true">
          新建
        </el-button>
      </div>
      <el-scrollbar height="calc(100vh - 52px)">
        <el-menu :default-active="selectedKbId" @select="selectKnowledgeBase" class="border-t">
          <el-menu-item v-for="kb in knowledgeBases" :key="kb.id" :index="kb.id">
            <div class="flex items-center justify-between w-full">
              <div class="flex flex-col">
                <span class="text-foreground font-medium">{{ kb.name }}</span>
                <span class="text-xs text-muted-foreground">{{ kb.description }}</span>
              </div>
              <div class="flex items-center gap-2">
                <el-button text :icon="Edit" @click.stop="renameKnowledgeBase(kb.id)" />
                <el-button text :icon="Delete" @click.stop="deleteKnowledgeBase(kb.id)" />
              </div>
            </div>
          </el-menu-item>
        </el-menu>
      </el-scrollbar>
    </el-aside>

    <el-container>
      <el-header height="56px" class="border-b flex items-center justify-between px-4">
        <div class="flex items-center gap-2">
          <el-icon><Document /></el-icon>
          <span class="font-medium">{{ currentKb?.name || '未选择知识库' }}</span>
        </div>
        <div class="flex items-center gap-2">
          <el-input v-model="fileSearch" placeholder="搜索文件..." size="small" class="w-64" />
          <el-upload
            multiple
            :show-file-list="false"
            :auto-upload="false"
            :on-change="onUploadChange"
            accept=".pdf,.xlsx"
          >
            <el-button type="primary" size="small" :icon="UploadIcon">添加文件</el-button>
          </el-upload>
        </div>
      </el-header>
      <el-main class="p-0">
        <el-table :data="filteredFiles" table-layout="auto" height="calc(100vh - 56px)">
          <el-table-column prop="name" label="文件名" min-width="240" />
          <el-table-column prop="type" label="类型" width="180" />
          <el-table-column prop="chunkCount" label="Chunk 数" width="120" />
          <el-table-column prop="createdAt" label="上传时间" width="180">
            <template #default="{ row }">
              {{ new Date(row.createdAt).toLocaleString() }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="240">
            <template #default="{ row }">
              <el-button size="small" @click="viewChunks(row.id)">查看片段</el-button>
              <el-button type="primary" size="small" @click="vectorizeFile(row.name)">向量化</el-button>
              <el-button type="danger" size="small" @click="removeFile(row.id)">删除</el-button>
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
