<template>
  <div class="qna-page">
    <div class="qna-toolbar">
      <el-button plain size="small" @click="toggleHistory">
        {{ historyCollapsed ? '显示对话历史' : '隐藏对话历史' }}
      </el-button>
      <el-button size="small" type="primary" @click="startNewChat">+ 新对话</el-button>
    </div>

    <div class="qna-layout" :class="{ collapsed: historyCollapsed }">
      <aside v-show="!historyCollapsed" class="history-sidebar">
        <div class="sidebar-header">
          <h3>对话历史</h3>
        </div>
        <div class="history-list">
          <div
            v-for="chat in conversations"
            :key="chat.id"
            class="history-item"
            :class="{ active: currentConversationId === chat.id }"
            @click="loadConversation(chat.id)"
          >
            <span class="chat-title">{{ chat.title || '新对话' }}</span>
            <span class="chat-time">{{ formatTime(chat.updated_at) }}</span>
          </div>
          <div v-if="!conversations.length" class="history-empty">暂无历史对话</div>
        </div>
      </aside>

      <main class="chat-main">
        <div class="chat-header">
          <div class="chat-title-wrap">
            <h2>{{ currentConversationId ? '继续对话' : '病虫害智能问答' }}</h2>
            <p class="chat-intro">基于知识库与 DeepSeek AI 的约束分析助手</p>
          </div>
          <div class="filter-row">
            <el-select v-model="cropType" placeholder="作物类型" clearable size="small" style="width: 110px;">
              <el-option label="玉米" value="玉米" />
              <el-option label="小麦" value="小麦" />
              <el-option label="水稻" value="水稻" />
            </el-select>
            <el-select v-model="category" placeholder="病害/虫害" clearable size="small" style="width: 110px;">
              <el-option label="虫害" value="虫害" />
              <el-option label="病害" value="病害" />
            </el-select>
          </div>
        </div>

        <div class="messages-container" ref="messagesContainer">
          <div v-if="!messages.length && !loading" class="welcome-message">
            <div class="welcome-icon">💬</div>
            <h3>您好，我是病虫害智能问答助手</h3>
            <p>我可以帮您解答病虫害识别、防治和种植管理问题</p>
            <div class="quick-questions">
              <span>快速提问：</span>
              <el-button v-for="q in quickQuestions" :key="q" size="small" @click="sendMessage(q)">
                {{ q }}
              </el-button>
            </div>
          </div>

          <div v-for="(msg, index) in messages" :key="index" class="message-item" :class="msg.role">
            <div class="message-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
            <div class="message-content">
              <div class="message-text" v-html="formatMessage(msg.content)"></div>
              <div v-if="msg.sources?.length" class="message-sources">
                <span class="sources-label">📚 参考来源：</span>
                <el-tag
                  v-for="source in msg.sources"
                  :key="source.id"
                  size="small"
                  class="source-tag"
                  @click="viewSource(source)"
                >
                  {{ source.disease_name || source.title }}
                  <span class="source-meta">{{ source.crop_type }} {{ source.category }}</span>
                </el-tag>
              </div>
              <div class="message-time">{{ formatTime(msg.created_at) }}</div>
            </div>
          </div>

          <div v-if="loading" class="message-item assistant">
            <div class="message-avatar">🤖</div>
            <div class="message-content">
              <div class="typing-indicator">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>

          <div v-if="sendError" class="inline-error-card">
            <el-alert :title="sendError" type="error" show-icon :closable="false" />
            <div class="error-actions">
              <el-button size="small" type="primary" :disabled="loading || !lastFailedQuestion" @click="retryLastQuestion">
                重试发送
              </el-button>
              <el-button size="small" :disabled="loading" @click="sendError = ''">关闭</el-button>
            </div>
          </div>
        </div>

        <div class="input-area">
          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="2"
            placeholder="输入您的问题..."
            resize="none"
            @keydown.enter.ctrl="handleSend"
          />
          <div class="input-actions">
            <span class="hint">按 Ctrl+Enter 发送</span>
            <el-button type="primary" :disabled="!inputMessage.trim() || loading" @click="handleSend">
              发送
            </el-button>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { qnaApi } from '@/api'

const conversations = ref([])
const currentConversationId = ref(null)
const messages = ref([])
const inputMessage = ref('')
const loading = ref(false)
const messagesContainer = ref(null)
const cropType = ref('')
const category = ref('')
const sendError = ref('')
const lastFailedQuestion = ref('')
const historyCollapsed = ref(false)

const quickQuestions = [
  '水稻叶片发黄是什么原因？',
  '如何防治稻飞虱？',
  '纹枯病的最佳防治时间是什么时候？'
]

function toggleHistory() {
  historyCollapsed.value = !historyCollapsed.value
}

function formatTime(time) {
  if (!time) return ''
  const d = new Date(time)
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function formatMessage(content) {
  if (!content) return ''
  const text = escapeHtml(String(content))
  const lines = text.split('\n')
  const blocks = []
  let i = 0

  while (i < lines.length) {
    const raw = lines[i].trim()
    if (!raw) {
      i += 1
      continue
    }

    if (raw.startsWith('### ')) {
      blocks.push(`<h4>${applyInlineMarkdown(raw.slice(4))}</h4>`)
      i += 1
      continue
    }
    if (raw.startsWith('## ')) {
      blocks.push(`<h3>${applyInlineMarkdown(raw.slice(3))}</h3>`)
      i += 1
      continue
    }
    if (raw.startsWith('# ')) {
      blocks.push(`<h2>${applyInlineMarkdown(raw.slice(2))}</h2>`)
      i += 1
      continue
    }

    if (/^\d+\.\s+/.test(raw)) {
      const items = []
      while (i < lines.length) {
        const line = lines[i].trim()
        if (!/^\d+\.\s+/.test(line)) break
        items.push(`<li>${applyInlineMarkdown(line.replace(/^\d+\.\s+/, ''))}</li>`)
        i += 1
      }
      blocks.push(`<ol>${items.join('')}</ol>`)
      continue
    }

    if (/^[-*]\s+/.test(raw)) {
      const items = []
      while (i < lines.length) {
        const line = lines[i].trim()
        if (!/^[-*]\s+/.test(line)) break
        items.push(`<li>${applyInlineMarkdown(line.replace(/^[-*]\s+/, ''))}</li>`)
        i += 1
      }
      blocks.push(`<ul>${items.join('')}</ul>`)
      continue
    }

    const paras = []
    while (i < lines.length) {
      const line = lines[i].trim()
      if (!line || line.startsWith('#') || /^\d+\.\s+/.test(line) || /^[-*]\s+/.test(line)) break
      paras.push(applyInlineMarkdown(line))
      i += 1
    }
    blocks.push(`<p>${paras.join('<br>')}</p>`)
  }

  return blocks.join('')
}

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function applyInlineMarkdown(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
}

async function fetchConversations() {
  try {
    const res = await qnaApi.conversations({ page: 1, page_size: 50 })
    conversations.value = res.items || []
  } catch (e) {
    conversations.value = []
    ElMessage.error('获取对话历史失败，请稍后重试')
  }
}

async function loadConversation(id) {
  try {
    currentConversationId.value = id
    const res = await qnaApi.conversationDetail(id)
    messages.value = res.messages || []
    scrollToBottom()
  } catch (e) {
    messages.value = []
    ElMessage.error('加载对话失败，请稍后重试')
    scrollToBottom()
  }
}

function startNewChat() {
  currentConversationId.value = null
  messages.value = []
}

async function handleSend() {
  const text = inputMessage.value.trim()
  if (!text || loading.value) return
  sendMessage(text, { isRetry: false })
}

async function sendMessage(text, options = { isRetry: false }) {
  if (!options.isRetry) {
    inputMessage.value = ''
    messages.value.push({
      role: 'user',
      content: text,
      created_at: new Date().toISOString()
    })
  }
  loading.value = true
  sendError.value = ''
  scrollToBottom()

  try {
    const res = await qnaApi.ask({
      question: text,
      conversation_id: currentConversationId.value || undefined,
      crop_type: cropType.value || undefined,
      category: category.value || undefined
    })

    messages.value.push({
      role: 'assistant',
      content: res.answer,
      sources: res.sources || [],
      created_at: new Date().toISOString()
    })

    if (res.conversation_id) {
      currentConversationId.value = res.conversation_id
      fetchConversations()
    }
  } catch (e) {
    ElMessage.error('发送失败，请重试')
    lastFailedQuestion.value = text
    sendError.value = e?.response?.data?.detail || '请求失败，请检查网络或稍后重试'
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function retryLastQuestion() {
  if (!lastFailedQuestion.value || loading.value) return
  sendMessage(lastFailedQuestion.value, { isRetry: true })
}

function viewSource(source) {
  window.open(`/knowledge/${source.id}`, '_blank')
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

watch(messages, () => scrollToBottom(), { deep: true })

onMounted(() => {
  if (window.innerWidth < 992) {
    historyCollapsed.value = true
  }
  fetchConversations()
})
</script>

<style scoped lang="scss">
.qna-page {
  height: calc(100vh - 96px);
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: hidden;
}

.qna-toolbar {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-shrink: 0;
}

.qna-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 12px;
  min-height: 0;
  flex: 1;
  overflow: hidden;
}

.qna-layout.collapsed {
  grid-template-columns: minmax(0, 1fr);
}

.history-sidebar {
  border: 1px solid var(--border-light);
  background: var(--surface-1);
  border-radius: var(--radius-lg);
  padding: 14px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.sidebar-header h3 {
  margin: 0 0 10px;
  font-size: 16px;
}

.history-list {
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-item {
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: 10px;
  cursor: pointer;
  transition: all .2s;
}

.history-item:hover {
  border-color: var(--primary);
}

.history-item.active {
  background: rgba(59, 130, 246, 0.12);
  border-color: var(--primary);
}

.chat-title {
  display: block;
  font-size: 14px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-time {
  display: block;
  font-size: 12px;
  margin-top: 4px;
  color: var(--text-secondary);
}

.history-empty {
  font-size: 12px;
  color: var(--text-muted);
  padding: 8px 2px;
}

.chat-main {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border-light);
  background: var(--surface-1);
  border-radius: var(--radius-lg);
  min-height: 0;
  height: 100%;
  overflow: hidden;
}

.chat-header {
  padding: 16px;
  border-bottom: 1px solid var(--border-light);
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.chat-title-wrap h2 {
  margin: 0 0 4px;
  font-size: 20px;
}

.chat-intro {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
}

.filter-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.messages-container {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px;
}

.welcome-message {
  text-align: center;
  padding: 24px 16px;
}

.welcome-icon {
  font-size: 48px;
}

.welcome-message h3 {
  margin: 10px 0 8px;
}

.welcome-message p {
  margin: 0;
  color: var(--text-secondary);
}

.quick-questions {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.quick-questions span {
  font-size: 13px;
  color: var(--text-secondary);
  align-self: center;
}

.message-item {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.message-item.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--surface-2);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message-content {
  max-width: min(78%, 700px);
}

.message-text {
  border-radius: 12px;
  padding: 10px 12px;
  line-height: 1.7;
  background: var(--surface-2);
  font-size: 14px;
  color: var(--text-primary);
}

.message-text :deep(h2),
.message-text :deep(h3),
.message-text :deep(h4) {
  margin: 8px 0 6px;
  line-height: 1.4;
}

.message-text :deep(p) {
  margin: 6px 0;
}

.message-text :deep(ol),
.message-text :deep(ul) {
  margin: 6px 0;
  padding-left: 20px;
}

.user .message-text {
  background: var(--primary);
  color: #fff;
}

.message-time {
  font-size: 11px;
  margin-top: 4px;
  color: var(--text-muted);
}

.message-sources {
  margin-top: 6px;
  padding: 8px;
  border-radius: var(--radius-sm);
  background: rgba(16, 185, 129, 0.08);
}

.sources-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.source-tag {
  margin-top: 6px;
  margin-right: 6px;
  cursor: pointer;
}

.source-meta {
  font-size: 11px;
  opacity: 0.7;
  margin-left: 4px;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 10px 12px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: .2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: .4s;
}

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}

.inline-error-card {
  margin-top: 8px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: 10px;
}

.error-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}

.input-area {
  padding: 12px 16px;
  border-top: 1px solid var(--border-light);
}

.input-actions {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.hint {
  font-size: 12px;
  color: var(--text-secondary);
}

@media (max-width: 991px) {
  .qna-page {
    height: calc(100vh - 96px);
    min-height: 0;
  }

  .chat-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .message-content {
    max-width: 88%;
  }
}
</style>
