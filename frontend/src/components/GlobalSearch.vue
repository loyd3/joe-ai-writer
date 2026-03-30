<template>
  <div class="global-search-trigger" @click="openSearch">
    <el-input
      :model-value="''"
      placeholder="搜索项目、文档内容..."
      prefix-icon="Search"
      readonly
      class="search-input"
    />
    <div class="search-shortcut">
      <kbd>⌘</kbd><kbd>K</kbd>
    </div>
  </div>
  
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="showModal" class="global-search-modal" @click.self="closeSearch">
        <div class="search-container">
          <div class="search-header">
            <el-input
              ref="searchInputRef"
              v-model="searchQuery"
              placeholder="输入关键词搜索文档内容..."
              prefix-icon="Search"
              clearable
              size="large"
              class="search-input-main"
              @input="handleInput"
              @keydown.enter="performSearch"
              @keydown.escape="closeSearch"
            >
              <template #suffix>
                <div class="input-actions">
                  <el-tag v-if="searchMode === 'enhanced'" size="small" type="success">增强搜索</el-tag>
                  <el-tag v-else-if="searchMode === 'semantic'" size="small" type="warning">语义搜索</el-tag>
                  <el-divider direction="vertical" />
                  <span class="shortcut-hint">ESC 关闭</span>
                </div>
              </template>
            </el-input>
          </div>
          
          <div class="search-body" ref="searchBodyRef">
            <div v-if="!hasSearched && recentSearches.length > 0" class="recent-searches">
              <div class="section-header">
                <span class="section-title">最近搜索</span>
                <el-button text type="primary" size="small" @click="clearRecentSearches">清空</el-button>
              </div>
              <div class="recent-items">
                <div
                  v-for="(item, index) in recentSearches"
                  :key="index"
                  class="recent-item"
                  @click="searchFromRecent(item)"
                >
                  <el-icon><Clock /></el-icon>
                  <span>{{ item }}</span>
                </div>
              </div>
            </div>
            
            <div v-if="isLoading" class="loading-state">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>正在搜索...</span>
            </div>
            
            <div v-else-if="isIndexing" class="loading-state">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>正在建立搜索索引...</span>
            </div>
            
            <div v-else-if="hasSearched" class="search-results">
              <div v-if="enhancedResults.length > 0" class="results-section">
                <div class="section-header">
                  <span class="section-title">内容匹配</span>
                  <span class="result-count">{{ enhancedResults.length }} 条结果</span>
                </div>
                
                <div class="results-list">
                  <div
                    v-for="(result, index) in enhancedResults"
                    :key="`result-${result.document_id}-${result.chunk_index}`"
                    class="result-card"
                    :class="{ active: activeResultIndex === index }"
                    @click="goToResult(result)"
                    @mouseenter="activeResultIndex = index"
                  >
                    <div class="result-main">
                      <div class="result-header">
                        <div class="doc-info">
                          <el-icon class="doc-icon"><Document /></el-icon>
                          <span class="doc-title">{{ result.document_title }}</span>
                        </div>
                        <div class="result-score">
                          <el-progress 
                            :percentage="Math.round(result.score * 100)" 
                            :stroke-width="6"
                            :show-text="false"
                            :color="getScoreColor(result.score)"
                          />
                          <span class="score-value">{{ (result.score * 100).toFixed(0) }}%</span>
                        </div>
                      </div>
                      
                      <div class="result-meta">
                        <span class="project-name">
                          <el-icon><Folder /></el-icon>
                          {{ result.project_title }}
                        </span>
                        <span v-if="result.block_type" class="block-type">
                          {{ getBlockTypeLabel(result.block_type) }}
                        </span>
                        <span class="position-info">
                          位置: {{ formatOffset(result.start_offset) }}
                        </span>
                      </div>
                      
                      <div class="result-content">
                        <span v-if="result.context_before" class="context before">{{ result.context_before }}</span>
                        <span class="highlighted-content" v-html="highlightContent(result.content, result.highlights)"></span>
                        <span v-if="result.context_after" class="context after">{{ result.context_after }}</span>
                      </div>
                    </div>
                    
                    <div class="result-footer">
                      <el-tag 
                        :type="result.match_type === 'semantic' ? 'warning' : 'success'" 
                        size="small"
                        effect="light"
                      >
                        {{ result.match_type === 'semantic' ? '语义匹配' : '关键词匹配' }}
                      </el-tag>
                      <span class="action-hint">
                        <el-icon><Position /></el-icon>
                        点击跳转
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              
              <div v-else class="empty-state">
                <el-icon class="empty-icon"><Search /></el-icon>
                <p class="empty-title">未找到相关内容</p>
                <p class="empty-hint">尝试使用不同的关键词，或检查搜索设置</p>
                <div v-if="indexStats.total_chunks === 0" class="index-hint">
                  <p>搜索索引为空，请先建立索引</p>
                  <el-button type="primary" @click="initIndex" :loading="isIndexing">
                    建立搜索索引
                  </el-button>
                </div>
              </div>
            </div>
            
            <div v-else-if="!hasSearched && recentSearches.length === 0" class="initial-state">
              <el-icon class="initial-icon"><Search /></el-icon>
              <p class="initial-title">开始搜索</p>
              <p class="initial-hint">输入关键词搜索所有文档内容</p>
              
              <div v-if="indexStats.total_chunks === 0" class="index-warning">
                <el-icon><WarningFilled /></el-icon>
                <span>搜索索引为空，需要先建立索引才能搜索</span>
                <el-button type="primary" size="small" @click="initIndex" :loading="isIndexing">
                  建立索引
                </el-button>
              </div>
              
              <div v-else class="index-status">
                <el-icon><CircleCheckFilled /></el-icon>
                <span>已索引 {{ indexStats.total_documents }} 个文档，{{ indexStats.total_chunks }} 个片段</span>
              </div>
              
              <div class="search-tips">
                <div class="tip-item">
                  <el-icon><Key /></el-icon>
                  <span>支持语义搜索，理解你的搜索意图</span>
                </div>
                <div class="tip-item">
                  <el-icon><Location /></el-icon>
                  <span>精确定位到文档中的具体位置</span>
                </div>
                <div class="tip-item">
                  <el-icon><Document /></el-icon>
                  <span>搜索所有项目和文档内容</span>
                </div>
              </div>
            </div>
          </div>
          
          <div class="search-footer">
            <div class="footer-left">
              <span class="footer-item">
                <kbd>↑</kbd><kbd>↓</kbd> 选择
              </span>
              <span class="footer-item">
                <kbd>Enter</kbd> 打开
              </span>
              <span class="footer-item">
                <kbd>Esc</kbd> 关闭
              </span>
            </div>
            <div class="footer-right">
              <el-button 
                v-if="indexStats.total_chunks > 0"
                text 
                size="small" 
                @click="initIndex" 
                :loading="isIndexing"
                title="重新建立索引"
              >
                <el-icon><Refresh /></el-icon>
                重建索引
              </el-button>
              <el-switch
                v-model="useSemanticSearch"
                size="small"
                active-text="语义搜索"
                inactive-text="关键词"
              />
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { searchApi, type SearchResultItem, type SearchStats } from '@/api/search-export'
import { debounce } from '@/utils/debounce'
import { 
  Search, Document, Folder, Position, Clock, Key, Location, Loading,
  WarningFilled, CircleCheckFilled, Refresh
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()

const showModal = ref(false)
const searchQuery = ref('')
const hasSearched = ref(false)
const isLoading = ref(false)
const isIndexing = ref(false)
const enhancedResults = ref<SearchResultItem[]>([])
const searchMode = ref<'normal' | 'enhanced' | 'semantic'>('enhanced')
const useSemanticSearch = ref(true)
const recentSearches = ref<string[]>([])
const activeResultIndex = ref(0)
const searchInputRef = ref()
const searchBodyRef = ref()
const indexStats = ref<SearchStats>({
  total_chunks: 0,
  total_documents: 0,
  projects: {},
  embedding_model_loaded: false
})

const RECENT_SEARCH_KEY = 'recent_searches'
const MAX_RECENT = 5

onMounted(() => {
  loadRecentSearches()
  document.addEventListener('keydown', handleGlobalKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleGlobalKeydown)
})

function handleGlobalKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    openSearch()
  }
  
  if (showModal.value) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      navigateResults(1)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      navigateResults(-1)
    } else if (e.key === 'Enter' && enhancedResults.value.length > 0) {
      e.preventDefault()
      goToResult(enhancedResults.value[activeResultIndex.value])
    }
  }
}

function navigateResults(direction: number) {
  const maxIndex = enhancedResults.value.length - 1
  activeResultIndex.value = Math.max(0, Math.min(maxIndex, activeResultIndex.value + direction))
  scrollToActiveResult()
}

function scrollToActiveResult() {
  nextTick(() => {
    const activeEl = searchBodyRef.value?.querySelector('.result-card.active')
    activeEl?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  })
}

async function openSearch() {
  showModal.value = true
  await loadIndexStats()
  nextTick(() => {
    searchInputRef.value?.focus()
  })
}

function closeSearch() {
  showModal.value = false
  searchQuery.value = ''
  hasSearched.value = false
  enhancedResults.value = []
  activeResultIndex.value = 0
}

async function loadIndexStats() {
  try {
    const res = await searchApi.getStats()
    indexStats.value = res.data
  } catch (error) {
    console.error('获取索引状态失败:', error)
  }
}

async function initIndex() {
  isIndexing.value = true
  try {
    const res = await searchApi.indexAll()
    indexStats.value = {
      total_chunks: res.data.total_chunks,
      total_documents: res.data.indexed_documents,
      projects: {},
      embedding_model_loaded: true
    }
    ElMessage.success(`索引完成：${res.data.indexed_documents} 个文档，${res.data.total_chunks} 个片段`)
  } catch (error) {
    console.error('建立索引失败:', error)
    ElMessage.error('建立索引失败，请稍后重试')
  } finally {
    isIndexing.value = false
  }
}

function loadRecentSearches() {
  try {
    const saved = localStorage.getItem(RECENT_SEARCH_KEY)
    if (saved) {
      recentSearches.value = JSON.parse(saved)
    }
  } catch {
    recentSearches.value = []
  }
}

function saveRecentSearch(query: string) {
  const searches = recentSearches.value.filter(s => s !== query)
  searches.unshift(query)
  recentSearches.value = searches.slice(0, MAX_RECENT)
  localStorage.setItem(RECENT_SEARCH_KEY, JSON.stringify(recentSearches.value))
}

function clearRecentSearches() {
  recentSearches.value = []
  localStorage.removeItem(RECENT_SEARCH_KEY)
}

function searchFromRecent(query: string) {
  searchQuery.value = query
  performSearch()
}

const debouncedSearch = debounce(async (query: string) => {
  if (!query || query.length < 2) {
    enhancedResults.value = []
    hasSearched.value = false
    return
  }
  
  if (indexStats.value.total_chunks === 0) {
    enhancedResults.value = []
    hasSearched.value = true
    return
  }
  
  isLoading.value = true
  hasSearched.value = true
  
  try {
    const res = await searchApi.enhancedSearch({
      q: query,
      use_semantic: useSemanticSearch.value,
      use_keyword: true,
      top_k: 30,
      min_score: 0.15
    })
    
    enhancedResults.value = res.data.results
    activeResultIndex.value = 0
  } catch (error) {
    console.error('搜索失败:', error)
    ElMessage.error('搜索失败，请稍后重试')
    enhancedResults.value = []
  } finally {
    isLoading.value = false
  }
}, 300)

function handleInput() {
  if (searchQuery.value.length >= 2) {
    debouncedSearch(searchQuery.value)
  } else {
    enhancedResults.value = []
    hasSearched.value = false
  }
}

async function performSearch() {
  if (!searchQuery.value.trim() || searchQuery.value.length < 2) return
  
  saveRecentSearch(searchQuery.value.trim())
  await debouncedSearch(searchQuery.value)
}

function goToResult(result: SearchResultItem) {
  closeSearch()
  router.push({
    path: `/document/${result.document_id}`,
    query: {
      highlight: searchQuery.value,
      blockId: result.block_id,
      offset: result.start_offset
    }
  })
}

function highlightContent(content: string, highlights: number[][]): string {
  if (!highlights || highlights.length === 0) {
    return escapeHtml(content)
  }
  
  let result = ''
  let lastEnd = 0
  const sortedHighlights = [...highlights].sort((a, b) => a[0] - b[0])
  
  for (const [start, end] of sortedHighlights) {
    if (start > lastEnd) {
      result += escapeHtml(content.slice(lastEnd, start))
    }
    result += `<mark class="highlight">${escapeHtml(content.slice(start, end))}</mark>`
    lastEnd = end
  }
  
  if (lastEnd < content.length) {
    result += escapeHtml(content.slice(lastEnd))
  }
  
  return result
}

function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

function getScoreColor(score: number): string {
  if (score >= 0.8) return '#67c23a'
  if (score >= 0.6) return '#e6a23c'
  if (score >= 0.4) return '#909399'
  return '#f56c6c'
}

function getBlockTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    paragraph: '段落',
    heading: '标题',
    quote: '引用',
    list: '列表',
    code: '代码'
  }
  return labels[type] || type
}

function formatOffset(offset: number): string {
  if (offset > 10000) {
    return `${(offset / 1000).toFixed(1)}k`
  }
  return String(offset)
}

watch(useSemanticSearch, () => {
  if (searchQuery.value.length >= 2) {
    debouncedSearch(searchQuery.value)
  }
})
</script>

<style scoped lang="scss">
.global-search-trigger {
  position: relative;
  cursor: pointer;
  
  .search-input {
    :deep(.el-input__wrapper) {
      border-radius: 10px;
      background: var(--coffee-bg-warm);
      box-shadow: none;
      cursor: pointer;
      
      &:hover {
        background: var(--coffee-bg-hover);
      }
    }
  }
  
  .search-shortcut {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    display: flex;
    gap: 2px;
    
    kbd {
      background: var(--coffee-bg-card);
      border: 1px solid var(--coffee-border);
      border-radius: 4px;
      padding: 2px 6px;
      font-size: 11px;
      font-family: inherit;
      color: var(--coffee-text-light);
    }
  }
}

.global-search-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  z-index: 9999;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 15vh;
}

.search-container {
  width: 680px;
  max-width: 90vw;
  max-height: 70vh;
  background: var(--coffee-bg-card);
  border-radius: 16px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.search-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--coffee-border);
  
  .search-input-main {
    :deep(.el-input__wrapper) {
      background: var(--coffee-bg-warm);
      border-radius: 12px;
      box-shadow: none;
      padding: 8px 16px;
      
      &.is-focus {
        box-shadow: 0 0 0 2px var(--coffee-primary-light);
      }
    }
    
    :deep(.el-input__inner) {
      font-size: 16px;
      
      &::placeholder {
        color: var(--coffee-text-light);
      }
    }
  }
  
  .input-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    
    .el-divider {
      margin: 0 4px;
    }
    
    .shortcut-hint {
      font-size: 12px;
      color: var(--coffee-text-light);
    }
  }
}

.search-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  min-height: 200px;
  max-height: calc(70vh - 140px);
}

.recent-searches {
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    margin-bottom: 8px;
  }
  
  .section-title {
    font-size: 12px;
    font-weight: 600;
    color: var(--coffee-text-light);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  
  .recent-items {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  
  .recent-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
    color: var(--coffee-text-secondary);
    
    &:hover {
      background: var(--coffee-bg-hover);
      color: var(--coffee-text);
    }
    
    .el-icon {
      font-size: 16px;
      color: var(--coffee-text-light);
    }
  }
}

.loading-state,
.empty-state,
.initial-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.loading-state {
  .el-icon {
    font-size: 32px;
    color: var(--coffee-primary);
    margin-bottom: 12px;
  }
  
  span {
    color: var(--coffee-text-light);
  }
}

.empty-state,
.initial-state {
  .empty-icon,
  .initial-icon {
    font-size: 48px;
    color: var(--coffee-text-light);
    opacity: 0.5;
    margin-bottom: 16px;
  }
  
  .empty-title,
  .initial-title {
    font-size: 16px;
    font-weight: 500;
    color: var(--coffee-text);
    margin-bottom: 8px;
  }
  
  .empty-hint,
  .initial-hint {
    font-size: 14px;
    color: var(--coffee-text-light);
    margin-bottom: 24px;
  }
}

.index-warning {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 16px 24px;
  background: rgba(230, 162, 60, 0.1);
  border: 1px solid rgba(230, 162, 60, 0.3);
  border-radius: 12px;
  margin-bottom: 24px;
  
  .el-icon {
    font-size: 24px;
    color: #e6a23c;
  }
  
  span {
    font-size: 14px;
    color: var(--coffee-text);
  }
}

.index-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: rgba(103, 194, 58, 0.1);
  border-radius: 8px;
  margin-bottom: 24px;
  font-size: 13px;
  color: var(--coffee-text-secondary);
  
  .el-icon {
    color: #67c23a;
  }
}

.index-hint {
  margin-top: 16px;
  padding: 16px;
  background: var(--coffee-bg-warm);
  border-radius: 12px;
  
  p {
    margin-bottom: 12px;
    font-size: 14px;
    color: var(--coffee-text-light);
  }
}

.initial-state {
  .search-tips {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px 24px;
    background: var(--coffee-bg-warm);
    border-radius: 12px;
    
    .tip-item {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 13px;
      color: var(--coffee-text-secondary);
      
      .el-icon {
        font-size: 16px;
        color: var(--coffee-primary);
      }
    }
  }
}

.search-results {
  .results-section {
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      margin-bottom: 8px;
    }
    
    .section-title {
      font-size: 12px;
      font-weight: 600;
      color: var(--coffee-text-light);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    
    .result-count {
      font-size: 12px;
      color: var(--coffee-text-light);
      background: var(--coffee-bg-warm);
      padding: 2px 8px;
      border-radius: 10px;
    }
  }
  
  .results-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  
  .result-card {
    padding: 14px 16px;
    border-radius: 12px;
    border: 1px solid var(--coffee-border);
    background: var(--coffee-bg-card);
    cursor: pointer;
    transition: all 0.2s;
    
    &:hover,
    &.active {
      background: var(--coffee-bg-hover);
      border-color: var(--coffee-primary-light);
      box-shadow: 0 4px 12px var(--coffee-shadow);
    }
    
    &.active {
      border-color: var(--coffee-primary);
    }
    
    .result-main {
      margin-bottom: 10px;
    }
    
    .result-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 8px;
    }
    
    .doc-info {
      display: flex;
      align-items: center;
      gap: 8px;
      
      .doc-icon {
        font-size: 18px;
        color: var(--coffee-primary);
      }
      
      .doc-title {
        font-size: 15px;
        font-weight: 600;
        color: var(--coffee-text);
      }
    }
    
    .result-score {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 100px;
      
      .el-progress {
        flex: 1;
      }
      
      .score-value {
        font-size: 12px;
        font-weight: 500;
        color: var(--coffee-text-light);
        min-width: 36px;
        text-align: right;
      }
    }
    
    .result-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 10px;
      font-size: 12px;
      color: var(--coffee-text-light);
      
      .project-name {
        display: flex;
        align-items: center;
        gap: 4px;
        color: var(--coffee-primary);
      }
      
      .block-type {
        padding: 2px 8px;
        background: var(--coffee-bg-warm);
        border-radius: 4px;
      }
      
      .position-info {
        font-family: monospace;
      }
    }
    
    .result-content {
      font-size: 13px;
      line-height: 1.7;
      color: var(--coffee-text-secondary);
      background: var(--coffee-bg-warm);
      padding: 12px 14px;
      border-radius: 8px;
      
      .context {
        color: var(--coffee-text-light);
        font-size: 12px;
        
        &.before::before {
          content: '...';
        }
        
        &.after::after {
          content: '...';
        }
      }
      
      .highlighted-content {
        :deep(.highlight) {
          background: rgba(255, 193, 7, 0.4);
          color: inherit;
          padding: 1px 4px;
          border-radius: 3px;
          font-weight: 500;
        }
      }
    }
    
    .result-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      .action-hint {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 12px;
        color: var(--coffee-text-light);
        
        .el-icon {
          font-size: 14px;
        }
      }
    }
  }
}

.search-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-top: 1px solid var(--coffee-border);
  background: var(--coffee-bg-warm);
  
  .footer-left {
    display: flex;
    gap: 16px;
  }
  
  .footer-item {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: var(--coffee-text-light);
    
    kbd {
      background: var(--coffee-bg-card);
      border: 1px solid var(--coffee-border);
      border-radius: 4px;
      padding: 2px 6px;
      font-size: 11px;
      font-family: inherit;
    }
  }
  
  .footer-right {
    display: flex;
    align-items: center;
    gap: 12px;
    
    :deep(.el-switch__label) {
      font-size: 12px;
    }
  }
}

.modal-enter-active,
.modal-leave-active {
  transition: all 0.25s ease;
  
  .search-container {
    transition: all 0.25s ease;
  }
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
  
  .search-container {
    transform: scale(0.95) translateY(-20px);
    opacity: 0;
  }
}
</style>
