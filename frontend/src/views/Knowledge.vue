<template>
  <div class="knowledge-page">
    <PageHeader title="知识库" subtitle="中国权威来源病虫害知识工作台（小麦/玉米/水稻）" />

    <section class="top-search card-lite">
      <div class="search-main">
        <el-input
          v-model="keyword"
          placeholder="搜索病虫害名称、症状、来源机构..."
          clearable
          size="large"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" size="large" @click="handleSearch">
          搜索
        </el-button>
        <el-button size="large" @click="resetAllFilters">
          重置
        </el-button>
      </div>

      <div class="quick-chips">
        <span class="chip-label">快捷过滤</span>
        <el-check-tag
          v-for="item in cropOptions"
          :key="item"
          :checked="cropType === item"
          @change="toggleCrop(item)"
        >
          {{ item }}
        </el-check-tag>
        <el-check-tag
          v-for="item in categoryOptions"
          :key="item"
          :checked="category === item"
          @change="toggleCategory(item)"
        >
          {{ item }}
        </el-check-tag>
      </div>
    </section>

    <section class="workspace">
      <aside class="filter-panel card-lite" :class="{ collapsed: !showFilters }">
        <div class="panel-header">
          <h3>筛选面板</h3>
          <el-button text @click="showFilters = !showFilters">
            {{ showFilters ? '收起' : '展开' }}
          </el-button>
        </div>

        <div v-show="showFilters" class="panel-body">
          <el-form label-position="top" class="filter-form">
            <el-form-item label="作物">
              <el-select v-model="cropType" clearable placeholder="全部作物">
                <el-option v-for="item in cropOptions" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>

            <el-form-item label="类别">
              <el-select v-model="category" clearable placeholder="全部类别">
                <el-option v-for="item in categoryOptions" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>

            <el-form-item label="形状特征">
              <el-select v-model="shape" clearable filterable placeholder="全部形状">
                <el-option v-for="item in shapeOptions" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>

            <el-form-item label="颜色特征">
              <el-select v-model="color" clearable filterable placeholder="全部颜色">
                <el-option v-for="item in colorOptions" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>

            <el-form-item label="来源类型">
              <el-select v-model="sourceType" clearable placeholder="全部来源类型">
                <el-option v-for="item in sourceTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>

            <el-form-item label="来源关键词">
              <el-input v-model="sourceName" clearable placeholder="如：农业农村部 / 中国农科院" />
            </el-form-item>

            <el-form-item label="更新时间">
              <el-select v-model="updatedPreset" placeholder="全部时间" @change="applyDatePreset">
                <el-option label="全部时间" value="all" />
                <el-option label="最近7天" value="7d" />
                <el-option label="最近30天" value="30d" />
                <el-option label="最近90天" value="90d" />
                <el-option label="自定义区间" value="custom" />
              </el-select>
            </el-form-item>

            <el-form-item v-if="updatedPreset === 'custom'" label="自定义日期">
              <el-date-picker
                v-model="customDateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                value-format="YYYY-MM-DD"
              />
            </el-form-item>
          </el-form>

          <div class="filter-actions">
            <el-button type="primary" @click="handleSearch">应用筛选</el-button>
            <el-button @click="resetAllFilters">清空</el-button>
          </div>
        </div>
      </aside>

      <main class="result-panel card-lite">
        <div class="result-toolbar">
          <div class="result-meta">
            <h3>{{ pageTitle }}</h3>
            <span>共 {{ total }} 条</span>
          </div>
          <div class="toolbar-actions">
            <el-radio-group v-model="viewMode" size="small">
              <el-radio-button label="card">卡片</el-radio-button>
              <el-radio-button label="list">列表</el-radio-button>
            </el-radio-group>
            <el-button :icon="RefreshRight" circle @click="fetchData" />
          </div>
        </div>

        <div v-if="loading" class="loading-wrap">
          <el-skeleton :rows="7" animated />
        </div>

        <template v-else>
          <div v-if="list.length && viewMode === 'card'" class="card-grid">
            <article v-for="item in list" :key="item.id" class="knowledge-card" @click="viewDetail(item.id)">
              <div class="card-top">
                <el-tag size="small" type="success">{{ item.crop_type }}</el-tag>
                <el-tag size="small" :type="item.category === '病害' ? 'danger' : 'warning'">{{ item.category }}</el-tag>
                <span class="updated-at">{{ formatDate(item.updated_at) }}</span>
              </div>
              <h4>{{ item.title }}</h4>
              <p class="summary">{{ item.symptoms }}</p>
              <div class="features">
                <span>形状：{{ item.shape || '-' }}</span>
                <span>颜色：{{ item.color || '-' }}</span>
              </div>
              <div class="source">
                <el-tag size="small" effect="plain">{{ sourceTypeText(item.source_type) }}</el-tag>
                <span>{{ item.source_name || '未标注来源' }}</span>
              </div>
            </article>
          </div>

          <div v-else-if="list.length && viewMode === 'list'" class="list-wrap">
            <div v-for="item in list" :key="item.id" class="list-row" @click="viewDetail(item.id)">
              <div class="list-main">
                <h4>{{ item.title }}</h4>
                <p>{{ item.symptoms }}</p>
              </div>
              <div class="list-side">
                <span>{{ item.crop_type }} / {{ item.category }}</span>
                <span>{{ sourceTypeText(item.source_type) }}</span>
                <span class="muted">{{ formatDate(item.updated_at) }}</span>
              </div>
            </div>
          </div>

          <EmptyState
            v-else
            title="没有匹配的知识条目"
            description="请调整筛选条件或关键词后重试"
            :icon="Reading"
          />
        </template>

        <div class="pagination-wrap">
          <el-pagination
            v-if="total > pageSize"
            v-model:current-page="page"
            :page-size="pageSize"
            :total="total"
            layout="total, prev, pager, next"
            @current-change="fetchData"
          />
        </div>
      </main>
    </section>

    <el-drawer
      v-model="showDetail"
      title="知识详情"
      size="560px"
      :with-header="true"
    >
      <div v-if="current" class="detail-body">
        <div class="detail-title">
          <h3>{{ current.title }}</h3>
          <div class="title-tags">
            <el-tag type="success">{{ current.crop_type }}</el-tag>
            <el-tag :type="current.category === '病害' ? 'danger' : 'warning'">{{ current.category }}</el-tag>
            <el-tag effect="plain">{{ sourceTypeText(current.source_type) }}</el-tag>
          </div>
        </div>

        <div class="detail-grid">
          <div><label>形状</label><span>{{ current.shape || '-' }}</span></div>
          <div><label>颜色</label><span>{{ current.color || '-' }}</span></div>
          <div><label>大小</label><span>{{ current.size || '-' }}</span></div>
          <div><label>更新</label><span>{{ formatDate(current.updated_at) }}</span></div>
        </div>

        <section class="detail-section">
          <h4>症状表现</h4>
          <p>{{ current.symptoms || '-' }}</p>
        </section>
        <section class="detail-section">
          <h4>发生条件</h4>
          <p>{{ current.conditions || '-' }}</p>
        </section>
        <section class="detail-section">
          <h4>防治建议</h4>
          <p>{{ current.prevention || '-' }}</p>
        </section>

        <section class="detail-section">
          <h4>标签</h4>
          <div class="tags">
            <el-tag v-for="tag in current.tags || []" :key="tag">{{ tag }}</el-tag>
          </div>
        </section>

        <section class="detail-section source-card">
          <h4>来源信息</h4>
          <p><strong>来源：</strong>{{ current.source_name || '-' }}</p>
          <p v-if="current.book_title"><strong>书名：</strong>{{ current.book_title }}</p>
          <p v-if="current.publisher"><strong>出版社：</strong>{{ current.publisher }}</p>
          <p v-if="current.publish_year"><strong>出版年份：</strong>{{ current.publish_year }}</p>
          <p v-if="current.chapter_ref"><strong>章节：</strong>{{ current.chapter_ref }}</p>
          <div class="source-actions">
            <el-button size="small" :icon="CopyDocument" @click="copySource(current)">复制来源</el-button>
            <el-button
              v-if="current.source_url"
              size="small"
              type="primary"
              :icon="Link"
              @click="openSource(current.source_url)"
            >
              打开链接
            </el-button>
          </div>
        </section>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument, Link, Reading, RefreshRight, Search } from '@element-plus/icons-vue'
import { knowledgeApi } from '@/api'
import EmptyState from '@/components/ui/EmptyState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const cropOptions = ['玉米', '小麦', '水稻']
const categoryOptions = ['虫害', '病害']
const sourceTypeOptions = [
  { label: '权威机构', value: 'official' },
  { label: '书本资料', value: 'book' },
  { label: '期刊资料', value: 'journal' }
]

const keyword = ref('')
const cropType = ref('')
const category = ref('')
const shape = ref('')
const color = ref('')
const sourceType = ref('')
const sourceName = ref('')
const updatedPreset = ref('all')
const customDateRange = ref([])

const showFilters = ref(true)
const viewMode = ref('card')
const loading = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 12
const shapeOptions = ref([])
const colorOptions = ref([])

const showDetail = ref(false)
const current = ref(null)

const pageTitle = computed(() => {
  const parts = []
  if (cropType.value) parts.push(cropType.value)
  if (category.value) parts.push(category.value)
  return parts.length ? `${parts.join('/')}知识条目` : '全部知识条目'
})

const dateRange = computed(() => {
  if (updatedPreset.value === 'custom' && customDateRange.value?.length === 2) {
    return { from: customDateRange.value[0], to: customDateRange.value[1] }
  }
  if (updatedPreset.value === 'all') return { from: undefined, to: undefined }
  const days = updatedPreset.value === '7d' ? 7 : updatedPreset.value === '30d' ? 30 : 90
  const end = new Date()
  const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000)
  return { from: toDateString(start), to: toDateString(end) }
})

function toDateString(value) {
  const year = value.getFullYear()
  const month = `${value.getMonth() + 1}`.padStart(2, '0')
  const day = `${value.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

function formatDate(value) {
  if (!value) return '-'
  const date = new Date(value)
  return date.toLocaleString('zh-CN')
}

function sourceTypeText(value) {
  const matched = sourceTypeOptions.find((item) => item.value === value)
  return matched ? matched.label : '未分类'
}

function toggleCrop(value) {
  cropType.value = cropType.value === value ? '' : value
  handleSearch()
}

function toggleCategory(value) {
  category.value = category.value === value ? '' : value
  handleSearch()
}

function applyDatePreset() {
  if (updatedPreset.value !== 'custom') {
    customDateRange.value = []
  }
}

function resetAllFilters() {
  keyword.value = ''
  cropType.value = ''
  category.value = ''
  shape.value = ''
  color.value = ''
  sourceType.value = ''
  sourceName.value = ''
  updatedPreset.value = 'all'
  customDateRange.value = []
  page.value = 1
  fetchData()
}

function handleSearch() {
  page.value = 1
  fetchData()
}

async function fetchFilters() {
  try {
    const [shapeRes, colorRes] = await Promise.all([
      knowledgeApi.shapes(),
      knowledgeApi.colors()
    ])
    shapeOptions.value = shapeRes.shapes || []
    colorOptions.value = colorRes.colors || []
  } catch {
    shapeOptions.value = []
    colorOptions.value = []
  }
}

async function fetchData() {
  loading.value = true
  try {
    const { from, to } = dateRange.value
    const res = await knowledgeApi.search({
      page: page.value,
      page_size: pageSize,
      keyword: keyword.value || undefined,
      crop_type: cropType.value || undefined,
      category: category.value || undefined,
      shape: shape.value || undefined,
      color: color.value || undefined,
      source_name: sourceName.value || undefined,
      source_type: sourceType.value || undefined,
      updated_from: from,
      updated_to: to
    })
    list.value = res.items || []
    total.value = res.total || 0
  } catch (error) {
    list.value = []
    total.value = 0
    ElMessage.error(error?.response?.data?.detail || '知识库查询失败')
  } finally {
    loading.value = false
  }
}

async function viewDetail(id) {
  try {
    const res = await knowledgeApi.detail(id)
    current.value = res
    showDetail.value = true
  } catch {
    ElMessage.error('获取知识详情失败')
  }
}

async function copySource(item) {
  const text = [
    item.source_name ? `来源：${item.source_name}` : '',
    item.book_title ? `书名：${item.book_title}` : '',
    item.publisher ? `出版社：${item.publisher}` : '',
    item.publish_year ? `年份：${item.publish_year}` : '',
    item.chapter_ref ? `章节：${item.chapter_ref}` : '',
    item.source_url ? `链接：${item.source_url}` : ''
  ].filter(Boolean).join('\n')

  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('来源信息已复制')
  } catch {
    ElMessage.warning('复制失败，请手动复制')
  }
}

function openSource(url) {
  window.open(url, '_blank')
}

onMounted(async () => {
  await fetchFilters()
  await fetchData()
})
</script>

<style scoped lang="scss">
.knowledge-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-lite {
  background: var(--surface-1);
  border: 1px solid var(--border-light);
  border-radius: 14px;
}

.top-search {
  padding: 14px;
}

.search-main {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 10px;
}

.quick-chips {
  margin-top: 12px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.chip-label {
  color: var(--text-muted);
  font-size: 12px;
}

.workspace {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 12px;
}

.filter-panel {
  padding: 12px;
  height: fit-content;
}

.filter-panel.collapsed {
  min-height: 64px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.panel-header h3 {
  margin: 0;
  font-size: 14px;
}

.filter-actions {
  display: flex;
  gap: 8px;
}

.result-panel {
  padding: 12px;
  min-height: 560px;
}

.result-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.result-meta {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.result-meta h3 {
  margin: 0;
  font-size: 16px;
}

.result-meta span {
  font-size: 12px;
  color: var(--text-muted);
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.loading-wrap {
  padding: 8px;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 10px;
}

.knowledge-card {
  border: 1px solid var(--border-light);
  border-radius: 12px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.18s ease;
  background: var(--surface-0);
}

.knowledge-card:hover {
  border-color: var(--primary);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.card-top {
  display: flex;
  align-items: center;
  gap: 6px;
}

.updated-at {
  margin-left: auto;
  color: var(--text-muted);
  font-size: 11px;
}

.knowledge-card h4 {
  margin: 10px 0 8px;
  font-size: 15px;
}

.summary {
  color: var(--text-secondary);
  margin: 0 0 10px;
  line-height: 1.6;
  font-size: 13px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.features {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}

.source {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 12px;
}

.list-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.list-row {
  border: 1px solid var(--border-light);
  border-radius: 10px;
  padding: 10px 12px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 220px;
  gap: 12px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.list-row:hover {
  border-color: var(--primary);
  background: color-mix(in srgb, var(--primary) 5%, var(--surface-0));
}

.list-main h4 {
  margin: 0 0 6px;
  font-size: 14px;
}

.list-main p {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary);
}

.list-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: center;
  gap: 4px;
  font-size: 12px;
}

.muted {
  color: var(--text-muted);
}

.pagination-wrap {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}

.detail-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.detail-title h3 {
  margin: 0 0 8px;
}

.title-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  border: 1px solid var(--border-light);
  border-radius: 10px;
  padding: 10px;
}

.detail-grid div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-grid label {
  font-size: 12px;
  color: var(--text-muted);
}

.detail-section h4 {
  margin: 0 0 6px;
  font-size: 14px;
}

.detail-section p {
  margin: 0;
  line-height: 1.7;
  color: var(--text-secondary);
  font-size: 13px;
}

.tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.source-card {
  border: 1px solid var(--border-light);
  border-radius: 10px;
  padding: 10px;
}

.source-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}

@media (max-width: 1024px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .filter-panel {
    order: 1;
  }

  .result-panel {
    order: 2;
  }
}

@media (max-width: 767px) {
  .search-main {
    grid-template-columns: 1fr;
  }

  .list-row {
    grid-template-columns: 1fr;
  }

  .list-side {
    align-items: flex-start;
  }
}
</style>
