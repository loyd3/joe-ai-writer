<template>
  <div class="global-search">
    <el-input
      v-model="searchQuery"
      placeholder="搜索项目、文档..."
      prefix-icon="Search"
      clearable
      @input="handleInput"
      @focus="showResults = true"
      @blur="handleBlur"
      @keyup.enter="performSearch"
    />
    
    <!-- 搜索建议下拉框 -->
    <div v-if="showResults && (suggestions.length > 0 || searchResults.total > 0)" class="search-dropdown">
      <!-- 搜索建议 -->
      <div v-if="suggestions.length > 0 && !hasSearched" class="suggestions-section">
        <div class="section-title">搜索建议</div>
        <div
          v-for="item in suggestions"
          :key="`${item.type}-${item.id}`"
          class="suggestion-item"
          @click="handleSuggestionClick(item)"
        >
          <el-icon v-if="item.type === 'project'"><Folder /></el-icon>
          <el-icon v-else><Document /></el-icon>
          <span class="suggestion-text">{{ item.text }}</span>
          <span class="suggestion-type">{{ item.type === 'project' ? '项目' : '文档' }}</span>
        </div>
      </div>
      
      <!-- 搜索结果 -->
      <div v-if="hasSearched" class="results-section">
        <!-- 项目结果 -->
        <div v-if="searchResults.projects.length > 0" class="result-group">
          <div class="section-title">
            <el-icon><Folder /></el-icon>
            项目 ({{ searchResults.projects.length }})
          </div>
          <div
            v-for="project in searchResults.projects"
            :key="`project-${project.id}`"
            class="result-item"
            @click="goToProject(project.id)"
          >
            <div class="result-title">{{ project.title }}</div>
            <div v-if="project.description" class="result-desc">{{ project.description }}</div>
          </div>
        </div>
        
        <!-- 文档结果 -->
        <div v-if="searchResults.documents.length > 0" class="result-group">
          <div class="section-title">
            <el-icon><Document /></el-icon>
            文档 ({{ searchResults.documents.length }})
          </div>
          <div
            v-for="doc in searchResults.documents"
            :key="`doc-${doc.id}`"
            class="result-item"
            @click="goToDocument(doc.id)"
          >
            <div class="result-title">{{ doc.title }}</div>
            <div class="result-meta">{{ doc.project_title }}</div>
            <div v-if="doc.snippet" class="result-snippet" v-html="highlightText(doc.snippet, searchQuery)" />
          </div>
        </div>
        
        <!-- 无结果 -->
        <div v-if="searchResults.total === 0" class="no-results">
          <el-icon><InfoFilled /></el-icon>
          <span>未找到相关内容</span>
        </div>
      </div>
    </div>
    
    <!-- 遮罩层 -->
    <div v-if="showResults" class="search-overlay" @click="showResults = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { searchApi } from '@/api/search-export'
import { debounce } from '@/utils/debounce'
import { Folder, Document, InfoFilled } from '@element-plus/icons-vue'

const router = useRouter()

const searchQuery = ref('')
const showResults = ref(false)
const hasSearched = ref(false)
const suggestions = ref<any[]>([])
const searchResults = ref({
  projects: [],
  documents: [],
  total: 0
})

// 防抖处理输入
const debouncedGetSuggestions = debounce(async (query: string) => {
  if (!query || query.length < 1) {
    suggestions.value = []
    return
  }
  
  try {
    const res = await searchApi.suggestions(query)
    suggestions.value = res.data.suggestions
  } catch {
    suggestions.value = []
  }
}, 200)

function handleInput() {
  hasSearched.value = false
  debouncedGetSuggestions(searchQuery.value)
}

function handleBlur() {
  // 延迟关闭，允许点击下拉项
  setTimeout(() => {
    showResults.value = false
  }, 200)
}

async function performSearch() {
  if (!searchQuery.value.trim()) return
  
  try {
    const res = await searchApi.search(searchQuery.value)
    searchResults.value = res.data
    hasSearched.value = true
  } catch {
    searchResults.value = { projects: [], documents: [], total: 0 }
  }
}

function handleSuggestionClick(item: any) {
  if (item.type === 'project') {
    goToProject(item.id)
  } else {
    goToDocument(item.id)
  }
}

function goToProject(id: number) {
  showResults.value = false
  router.push(`/project/${id}`)
}

function goToDocument(id: number) {
  showResults.value = false
  router.push(`/document/${id}`)
}

function highlightText(text: string, query: string): string {
  if (!query) return text
  const regex = new RegExp(`(${query})`, 'gi')
  return text.replace(regex, '<mark>$1</mark>')
}

// 监听搜索词变化，清空结果
watch(searchQuery, (newVal) => {
  if (!newVal) {
    hasSearched.value = false
    suggestions.value = []
  }
})
</script>

<style scoped lang="scss">
.global-search {
  position: relative;
  width: 230px;
  
  :deep(.el-input__wrapper) {
    border-radius: 20px;
    background: var(--coffee-bg-warm);
    box-shadow: none;
    
    &.is-focus {
      background: var(--coffee-bg-card);
      box-shadow: 0 0 0 2px var(--coffee-primary-light);
    }
  }
}

.search-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  background: var(--coffee-bg-card);
  border-radius: 12px;
  box-shadow: 0 8px 24px var(--coffee-shadow-hover);
  border: 1px solid var(--coffee-border);
  z-index: 1000;
  max-height: 400px;
  overflow-y: auto;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 16px 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--coffee-text-light);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.suggestions-section {
  padding: 4px 0;
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background: rgba(166, 94, 46, 0.06);
  }
  
  .el-icon {
    font-size: 16px;
    color: var(--coffee-text-light);
  }
  
  .suggestion-text {
    flex: 1;
    font-size: 14px;
    color: var(--coffee-text);
  }
  
  .suggestion-type {
    font-size: 12px;
    color: var(--coffee-text-light);
    padding: 2px 8px;
    background: var(--coffee-bg-warm);
    border-radius: 10px;
  }
}

.results-section {
  padding: 4px 0;
}

.result-group {
  margin-bottom: 8px;
}

.result-item {
  padding: 12px 16px;
  cursor: pointer;
  transition: all 0.2s;
  border-left: 3px solid transparent;
  
  &:hover {
    background: rgba(166, 94, 46, 0.06);
    border-left-color: var(--coffee-primary);
  }
  
  .result-title {
    font-size: 14px;
    font-weight: 500;
    color: var(--coffee-text);
    margin-bottom: 4px;
  }
  
  .result-desc {
    font-size: 13px;
    color: var(--coffee-text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .result-meta {
    font-size: 12px;
    color: var(--coffee-text-light);
    margin-bottom: 4px;
  }
  
  .result-snippet {
    font-size: 13px;
    color: var(--coffee-text-secondary);
    line-height: 1.5;
    
    :deep(mark) {
      background: rgba(166, 94, 46, 0.2);
      color: var(--coffee-primary-dark);
      padding: 0 2px;
      border-radius: 2px;
    }
  }
}

.no-results {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px;
  color: var(--coffee-text-light);
  
  .el-icon {
    font-size: 48px;
    margin-bottom: 12px;
    opacity: 0.5;
  }
}

.search-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 999;
}
</style>
