<template>
  <div class="qna-page">
    <PageHeader title="智能问答" subtitle="基于知识库与检测上下文的辅助问答" />
    <div class="qna-layout">
      <!-- 对话历史列表 -->
      <aside class="history-sidebar">
        <div class="sidebar-header">
          <h3>对话历史</h3>
          <el-button size="small" @click="startNewChat">+ 新对话</el-button>
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
        </div>
      </aside>

      <!-- 聊天主区域 -->
      <main class="chat-main">
        <div class="chat-header">
          <h2>{{ currentConversationId ? '继续对话' : '病虫害智能问答' }}</h2>
          <p class="chat-intro">基于知识库的智能问答助手，结合 DeepSeek AI 分析</p>
          <div class="filter-row">
            <el-select v-model="cropType" placeholder="作物类型" clearable size="small" style="width: 100px;">
              <el-option label="玉米" value="玉米" />
              <el-option label="小麦" value="小麦" />
              <el-option label="水稻" value="水稻" />
            </el-select>
            <el-select v-model="category" placeholder="类别" clearable size="small" style="width: 80px;">
              <el-option label="虫害" value="虫害" />
              <el-option label="病害" value="病害" />
            </el-select>
          </div>
        </div>

        <div class="messages-container" ref="messagesContainer">
          <div v-if="!messages.length && !loading" class="welcome-message">
            <div class="welcome-icon">💬</div>
            <h3>您好，我是病虫害智能问答助手</h3>
            <p>我可以帮您解答以下问题：</p>
            <ul>
              <li>病虫害的识别和诊断</li>
              <li>病虫害的防治方法和用药建议</li>
              <li>作物病害的发生条件和传播途径</li>
              <li>农业技术咨询和种植建议</li>
            </ul>
            <div class="quick-questions">
              <span>试试这样问：</span>
              <el-button v-for="q in quickQuestions" :key="q" size="small" @click="sendMessage(q)">{{ q }}</el-button>
            </div>
          </div>

          <div v-for="(msg, index) in messages" :key="index" class="message-item" :class="msg.role">
            <div class="message-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
            <div class="message-content">
              <div class="message-text" v-html="formatMessage(msg.content)"></div>
              <div v-if="msg.sources?.length" class="message-sources">
                <span class="sources-label">📚 参考来源：</span>
                <el-tag v-for="source in msg.sources" :key="source.id" size="small" class="source-tag" @click="viewSource(source)">
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
import PageHeader from '@/components/ui/PageHeader.vue'

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

const quickQuestions = [
  '水稻叶片发黄是什么原因？',
  '如何防治稻飞虱？',
  '纹枯病的最佳防治时间是什么时候？'
]

function formatTime(time) {
  if (!time) return ''
  const d = new Date(time)
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function formatMessage(content) {
  if (!content) return ''
  // 处理换行和基本格式
  return content
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
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
    
    // 添加助手回复
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
  // 跳转到知识详情
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
  fetchConversations()
})
</script>

<style lang="scss" scoped>
.qna-page { height: calc(100vh - 140px); display: flex; flex-direction: column; gap: 12px; }

.qna-layout { display: flex; width: 100%; gap: 24px; }

.history-sidebar {
  width: 280px; flex-shrink: 0;
  background: var(--bg-primary); border-radius: var(--radius-lg); padding: 16px;
  display: flex; flex-direction: column;
}
.sidebar-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; h3 { margin: 0; font-size: 16px; } }
.history-list { flex: 1; overflow-y: auto; }
.history-item {
  padding: 12px; border-radius: var(--radius-md); cursor: pointer; margin-bottom: 4px;
  transition: all 0.2s;
  &:hover { background: var(--bg-secondary); }
  &.active { background: var(--primary); color: white; }
  .chat-title { display: block; font-size: 14px; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .chat-time { font-size: 12px; opacity: 0.7; }
}

.chat-main {
  flex: 1; display: flex; flex-direction: column;
  background: var(--bg-primary); border-radius: var(--radius-lg); overflow: hidden;
}
.chat-header { padding: 20px 24px; border-bottom: 1px solid var(--border-light); h2 { margin: 0 0 8px; font-size: 18px; } .chat-intro { margin: 0 0 12px; font-size: 14px; color: var(--text-secondary); } .filter-row { display: flex; gap: 8px; } }

.messages-container { flex: 1; overflow-y: auto; padding: 24px; }

.welcome-message {
  text-align: center; padding: 48px 24px;
  .welcome-icon { font-size: 64px; margin-bottom: 24px; }
  h3 { margin: 0 0 16px; font-size: 20px; }
  p { color: var(--text-secondary); margin-bottom: 16px; }
  ul { text-align: left; max-width: 400px; margin: 0 auto 24px; color: var(--text-secondary); li { margin-bottom: 8px; } }
}
.quick-questions { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; align-items: center; span { font-size: 14px; color: var(--text-muted); } }

.message-item {
  display: flex; gap: 12px; margin-bottom: 24px;
  &.user { flex-direction: row-reverse; .message-content { align-items: flex-end; } }
  &.assistant { .message-avatar { background: var(--primary); } }
}
.message-avatar { width: 36px; height: 36px; border-radius: 50%; background: var(--bg-secondary); display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }
.message-content { max-width: 70%; }
.message-text { background: var(--bg-secondary); padding: 12px 16px; border-radius: var(--radius-lg); line-height: 1.6; font-size: 14px; }
.message-sources { margin-top: 8px; padding: 8px 12px; background: rgba(16, 185, 129, 0.1); border-radius: var(--radius-sm); .sources-label { font-size: 12px; color: var(--text-muted); margin-right: 8px; } .source-tag { cursor: pointer; margin-right: 4px; display: flex; gap: 4px; align-items: center; .source-meta { font-size: 11px; opacity: 0.7; } } }
.message-time { font-size: 11px; color: var(--text-muted); margin-top: 4px; }
.user .message-text { background: var(--primary); color: white; }

.typing-indicator { display: flex; gap: 4px; padding: 12px 16px; span { width: 8px; height: 8px; background: var(--text-muted); border-radius: 50%; animation: typing 1.4s infinite; &:nth-child(2) { animation-delay: 0.2s; } &:nth-child(3) { animation-delay: 0.4s; } } }
@keyframes typing { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-8px); } }

.inline-error-card {
  margin: 12px 0;
  padding: 12px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
}

.error-actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}

.input-area { padding: 16px 24px; border-top: 1px solid var(--border-light); }
.input-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; .hint { font-size: 12px; color: var(--text-muted); } }
</style>
