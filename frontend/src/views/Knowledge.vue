<template>
  <div class="knowledge-page">
    <PageHeader title="知识库" subtitle="按作物、类别和特征检索病虫害知识条目" />

    <div class="search-section">
      <div class="search-box">
        <el-input v-model="keyword" placeholder="搜索病虫害知识..." size="large" clearable @keyup.enter="handleSearch">
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" size="large" @click="handleSearch">搜索</el-button>
      </div>
      <div class="filter-row">
        <el-select v-model="cropType" placeholder="作物类型" clearable @change="handleSearch">
          <el-option label="玉米" value="玉米" />
          <el-option label="小麦" value="小麦" />
          <el-option label="水稻" value="水稻" />
        </el-select>
        <el-select v-model="category" placeholder="类别" clearable @change="handleSearch">
          <el-option label="虫害" value="虫害" />
          <el-option label="病害" value="病害" />
        </el-select>
        <el-select v-model="shape" placeholder="形状特征" clearable @change="handleSearch">
          <el-option v-for="s in shapeOptions" :key="s" :label="s" :value="s" />
        </el-select>
        <el-select v-model="color" placeholder="颜色特征" clearable @change="handleSearch">
          <el-option v-for="c in colorOptions" :key="c" :label="c" :value="c" />
        </el-select>
      </div>
    </div>

    <div class="content-layout">
      <main class="knowledge-main">
        <div class="section-header">
          <h2>{{ pageTitle }}</h2>
          <span class="result-count">共 {{ total }} 条</span>
        </div>

        <div v-if="loading" class="loading">
          <el-icon class="is-loading"><loading /></el-icon>
          加载中...
        </div>

        <div v-else-if="list.length" class="knowledge-list">
          <div v-for="item in list" :key="item.id" class="knowledge-card card" @click="viewDetail(item.id)">
            <div class="card-header">
              <span class="crop-tag">{{ item.crop_type }}</span>
              <span class="category-tag" :class="item.category">{{ item.category }}</span>
              <span class="update-time">{{ formatTime(item.updated_at) }}</span>
            </div>
            <h3 class="card-title">{{ item.title }}</h3>
            <div class="card-features">
              <span class="feature"><strong>形状：</strong>{{ item.shape }}</span>
              <span class="feature"><strong>颜色：</strong>{{ item.color }}</span>
            </div>
            <p class="card-summary">{{ item.symptoms }}</p>
            <div class="card-tags">
              <el-tag v-for="tag in item.tags" :key="tag" size="small">{{ tag }}</el-tag>
            </div>
          </div>
        </div>

        <EmptyState v-else title="暂无相关知识" description="可以调整筛选条件后重新搜索" :icon="Reading" />

        <el-pagination v-if="total > pageSize" layout="prev, pager, next" :total="total" v-model:current-page="page" :page-size="pageSize" @current-change="fetchData" />
      </main>
    </div>

    <el-dialog v-model="showDetail" title="知识详情" width="700px" class="knowledge-detail-dialog">
      <div v-if="current" class="detail-content">
        <div class="detail-header">
          <h2>{{ current.title }}</h2>
          <div class="detail-meta">
            <el-tag type="success">{{ current.crop_type }}</el-tag>
            <el-tag :type="current.category === '虫害' ? 'warning' : 'danger'">{{ current.category }}</el-tag>
            <span>更新时间：{{ formatTime(current.updated_at) }}</span>
          </div>
        </div>

        <div class="detail-features">
          <div class="feature-item">
            <span class="feature-label">形状特征</span>
            <span class="feature-value">{{ current.shape }}</span>
          </div>
          <div class="feature-item">
            <span class="feature-label">颜色特征</span>
            <span class="feature-value">{{ current.color }}</span>
          </div>
          <div class="feature-item">
            <span class="feature-label">尺寸大小</span>
            <span class="feature-value">{{ current.size }}</span>
          </div>
        </div>

        <el-tabs v-model="activeTab">
          <el-tab-pane label="症状表现" name="symptoms">
            <div class="content-section">{{ current.symptoms }}</div>
          </el-tab-pane>
          <el-tab-pane label="发生条件" name="conditions">
            <div class="content-section">{{ current.conditions }}</div>
          </el-tab-pane>
          <el-tab-pane label="防治方法" name="prevention">
            <div class="content-section">{{ current.prevention }}</div>
          </el-tab-pane>
        </el-tabs>

        <div class="detail-footer">
          <div class="tags">
            <span>标签：</span>
            <el-tag v-for="tag in current.tags" :key="tag">{{ tag }}</el-tag>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading, Reading, Search } from '@element-plus/icons-vue'
import { knowledgeApi } from '@/api'
import PageHeader from '@/components/ui/PageHeader.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const keyword = ref('')
const cropType = ref('')
const category = ref('')
const shape = ref('')
const color = ref('')
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 12
const loading = ref(false)
const showDetail = ref(false)
const current = ref(null)
const activeTab = ref('symptoms')

const shapeOptions = ref([])
const colorOptions = ref([])

const pageTitle = computed(() => {
  const parts = []
  if (cropType.value) parts.push(cropType.value)
  if (category.value) parts.push(category.value)
  return parts.length ? parts.join('/') : '全部病虫害知识'
})

const hotTags = ['稻飞虱', '纹枯病', '蚜虫', '赤霉病', '二化螟']

function formatTime(time) {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

async function fetchFilters() {
  try {
    const [shapesRes, colorsRes] = await Promise.all([
      knowledgeApi.shapes ? knowledgeApi.shapes() : Promise.resolve({ shapes: [] }),
      knowledgeApi.colors ? knowledgeApi.colors() : Promise.resolve({ colors: [] })
    ])
    shapeOptions.value = shapesRes.shapes || []
    colorOptions.value = colorsRes.colors || []
  } catch (e) {
    shapeOptions.value = ['椭圆形', '蠕虫形', '纺锤形', '蛾形', '梭形', '长条形', '圆形']
    colorOptions.value = ['黄绿色', '灰褐色', '黄褐色', '白色', '粉红色', '灰绿色', '红褐色']
  }
}

async function fetchData() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize,
      keyword: keyword.value || undefined,
      crop_type: cropType.value || undefined,
      category: category.value || undefined,
      shape: shape.value || undefined,
      color: color.value || undefined
    }
    const res = await knowledgeApi.search(params)
    list.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    list.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function fetchRecent() {
  try {
    const res = await knowledgeApi.recent({ page_size: 5 })
  } catch (e) {
    // ignore
  }
}

function handleSearch() {
  page.value = 1
  fetchData()
}

async function viewDetail(id) {
  try {
    const res = await knowledgeApi.detail(id)
    current.value = res
    showDetail.value = true
  } catch (e) {
    ElMessage.error('获取详情失败')
  }
}

onMounted(() => {
  fetchFilters()
  fetchData()
})
</script>

<style lang="scss" scoped>
.knowledge-page { max-width: 1200px; margin: 0 auto; }

.search-section { margin-bottom: 24px; }
.search-box { max-width: 500px; margin-bottom: 16px; }
.filter-row { display: flex; gap: 12px; flex-wrap: wrap;
  .el-select { width: 140px; }
}

.content-layout { display: grid; grid-template-columns: 1fr; gap: 24px; }

.knowledge-main {
  .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; h2 { margin: 0; font-size: 18px; } }
  .result-count { font-size: 14px; color: var(--text-muted); }
}
.loading { text-align: center; padding: 64px; color: var(--text-muted); }

.knowledge-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; }
.knowledge-card { cursor: pointer; transition: all 0.2s; &:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); } }
.card-header { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.crop-tag { padding: 4px 10px; background: #d1fae5; color: #065f46; border-radius: 4px; font-size: 12px; }
.category-tag { padding: 4px 10px; border-radius: 4px; font-size: 12px;
  &.虫害 { background: #fef3c7; color: #d97706; }
  &.病害 { background: #fee2e2; color: #dc2626; }
}
.update-time { font-size: 12px; color: var(--text-muted); margin-left: auto; }
.card-title { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
.card-features { display: flex; gap: 16px; margin-bottom: 8px; font-size: 13px;
  .feature { color: var(--text-secondary); }
}
.card-summary { font-size: 14px; color: var(--text-secondary); margin-bottom: 12px; line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.card-tags { display: flex; gap: 6px; flex-wrap: wrap; }

:deep(.knowledge-detail-dialog) {
  .detail-content { padding: 8px; }
  .detail-header { margin-bottom: 20px; h2 { margin: 0 0 12px; font-size: 22px; } }
  .detail-meta { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  .detail-features { display: flex; gap: 24px; padding: 16px; background: var(--bg-secondary); border-radius: var(--radius-md); margin-bottom: 20px; flex-wrap: wrap;
    .feature-item { display: flex; flex-direction: column; gap: 4px; }
    .feature-label { font-size: 12px; color: var(--text-muted); }
    .feature-value { font-size: 14px; font-weight: 500; }
  }
  .content-section { line-height: 1.8; color: var(--text-secondary); }
  .detail-footer { margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--border-light); }
  .tags { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; span { font-size: 14px; color: var(--text-muted); } }
}
</style>
