<template>
  <div class="market-container">
        <!-- 🌟 新增：数据源控制面板 -->
    <el-card class="source-control-card" shadow="never">
      <div class="control-row">
        <span class="label">📡 数据源状态：</span>
        
        <!-- 模式切换开关 -->
        <el-switch
          v-model="isAutoMode"
          active-text="自动切换"
          inactive-text="手动切换"
          inline-prompt
          @change="handleModeChange"
          style="margin-right: 15px;"
        />

        <!-- 手动模式下的下拉框 -->
        <el-select 
          v-if="!isAutoMode" 
          v-model="selectedSource" 
          size="small" 
          @change="handleSourceChange"
          style="width: 150px;"
        >
          <el-option 
            v-for="src in availableSources" 
            :key="src.name" 
            :label="src.name" 
            :value="src.name" 
          />
        </el-select>

        <!-- 当前状态标签 -->
        <el-tag :type="currentSourceType" size="small" effect="dark" style="margin-left: auto;">
          当前使用：{{ currentSourceName }}
        </el-tag>
      </div>
    </el-card>
    
    <el-card class="search-card">
      <template #header>
        <div class="card-header">
          <span>📈 实时行情监控</span>
          <el-tag :type="statusType" effect="dark" style="margin-left: 10px;">
            {{ statusText }}
          </el-tag>
        </div>
      </template>
      
      <el-form :inline="true" @submit.prevent="fetchData">
        <el-form-item label="股票代码">
          <el-input 
            v-model="symbolInput" 
            placeholder="例如: sh600519 或 600519" 
            style="width: 250px;"
            clearable
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchData" :loading="loading">查询</el-button>
          <el-button @click="toggleAutoRefresh">
            {{ autoRefresh ? '暂停刷新' : '自动刷新' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据展示区 -->
    <div v-if="currentData" class="data-display">
      <el-row :gutter="20">
        <!-- 主行情卡片 -->
        <el-col :span="24">
          <el-card shadow="hover" class="price-card">
            <div class="price-header">
              <h2>{{ currentData.name || '未知股票' }} <small>({{ currentData.symbol }})</small></h2>
              <el-tag :type="getPriceType(currentData.change_percent)" size="large">
                {{ currentData.source === 'realtime_bid_ask' ? '实时' : '延迟' }}
              </el-tag>
            </div>
            
            <div class="price-main">
              <span class="current-price" :class="getPriceColor(currentData.change_percent)">
                ¥ {{ formatNumber(currentData.price) }}
              </span>
              <span class="change-info" :class="getPriceColor(currentData.change_percent)">
                {{ formatNumber(currentData.change_percent) }}% 
                ({{ formatNumber(currentData.change_amount) }})
              </span>
            </div>

            <el-divider />

            <el-row :gutter="20" class="stats-row">
              <el-col :span="6" class="stat-item">
                <div class="stat-label">最高</div>
                <div class="stat-value">{{ formatNumber(currentData.high) }}</div>
              </el-col>
              <el-col :span="6" class="stat-item">
                <div class="stat-label">最低</div>
                <div class="stat-value">{{ formatNumber(currentData.low) }}</div>
              </el-col>
              <el-col :span="6" class="stat-item">
                <div class="stat-label">今开</div>
                <div class="stat-value">{{ formatNumber(currentData.open) }}</div>
              </el-col>
              <el-col :span="6" class="stat-item">
                <div class="stat-label">昨收</div>
                <div class="stat-value">{{ formatNumber(currentData.prev_close) }}</div>
              </el-col>
            </el-row>
            
            <el-row :gutter="20" class="stats-row" style="margin-top: 15px;">
              <el-col :span="8" class="stat-item">
                <div class="stat-label">成交量 (手)</div>
                <div class="stat-value">{{ formatVolume(currentData.volume) }}</div>
              </el-col>
              <el-col :span="8" class="stat-item">
                <div class="stat-label">成交额 (元)</div>
                <div class="stat-value">{{ formatVolume(currentData.amount) }}</div>
              </el-col>
              <el-col :span="8" class="stat-item">
                <div class="stat-label">更新时间</div>
                <div class="stat-value time-text">{{ currentData.time }}</div>
              </el-col>
            </el-row>

            <div v-if="currentData.message" class="alert-box">
              <el-icon><Warning /></el-icon>
              <span>{{ currentData.message }}</span>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 空状态 -->
    <el-empty v-else-if="!loading && !error" description="请输入股票代码开始监控" />
    
    <!-- 错误状态 -->
    <el-result v-if="error" icon="error" title="获取数据失败" :sub-title="error">
      <template #extra>
        <el-button type="primary" @click="fetchData">重试</el-button>
      </template>
    </el-result>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Warning } from '@element-plus/icons-vue'
import axios from 'axios'

// 配置 API 地址
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

// --- 新增：数据源状态变量 ---
const isAutoMode = ref(true)
const currentSourceName = ref('Loading...')
const currentSourceType = ref('info')
const availableSources = ref([])
const selectedSource = ref('')

// 获取数据源状态
const fetchSourceStatus = async () => {
  try {
    const res = await axios.get(`${API_BASE}/data/source/status`)
    
    // 更新模式
    isAutoMode.value = res.data.mode === 'auto'
    
    // 【关键】更新当前源名称
    // 确保这里的 res.data.current_source 确实是后端返回的最新值
    const newName = res.data.current_source
    if (currentSourceName.value !== newName) {
        console.log(`🔄 [前端] 检测到数据源变化：${currentSourceName.value} -> ${newName}`)
        currentSourceName.value = newName
    }
    
    availableSources.value = res.data.available_sources
    
    // 如果是手动模式，同步下拉框
    if (!isAutoMode.value) {
      selectedSource.value = currentSourceName.value
    }
    
    // 更新标签颜色
    currentSourceType.value = isAutoMode.value ? 'success' : 'warning'
    
  } catch (e) {
    console.error("获取数据源状态失败", e)
  }
}

// frontend/src/views/MarketView.vue

// 处理模式切换
const handleModeChange = async (val) => {
  const newMode = val ? 'auto' : 'manual'
  
  // 构造基础 payload
  const payload = { mode: newMode }
  
  // 【关键修复】如果是切换到手动模式，且当前没有选中的值，则默认选中“当前正在使用的数据源”
  if (!val) { 
    // 如果 selectedSource 为空，就用 currentSourceName 填充
    if (!selectedSource.value && currentSourceName.value) {
      selectedSource.value = currentSourceName.value
      console.log(`[自动填充] 切换到手动模式，默认选中当前源: ${selectedSource.value}`)
    }
    
    // 确保最终有值才发送
    if (selectedSource.value) {
      payload.source_name = selectedSource.value
    } else {
      // 极端情况：连当前源名字都不知道，先刷新一下状态再试，或者直接报错提示用户
      ElMessage.warning('正在同步数据源状态，请稍后再次切换')
      await fetchSourceStatus()
      isAutoMode.value = true // 暂时回滚开关
      return 
    }
  }

  try {
    await axios.post(`${API_BASE}/data/source/switch`, payload)
    ElMessage.success(val ? '已开启自动切换模式，系统将自动选择数据源' : `已开启手动切换模式 ，请自行选择数据源。当前数据源： (${payload.source_name})`)
    fetchSourceStatus() // 刷新状态标签
  } catch (e) {
    console.error(e)
    const msg = e.response?.data?.detail || '切换失败'
    ElMessage.error(msg)
    isAutoMode.value = !val // 出错回滚开关状态
  }
}

// 处理下拉框选择
const handleSourceChange = async (name) => {
  try {
    // 明确指定 mode 为 manual 并带上 name
    await axios.post(`${API_BASE}/data/source/switch`, { 
      mode: 'manual', 
      source_name: name 
    })
    ElMessage.success(`已锁定数据源：${name}`)
    fetchSourceStatus()
    fetchData() 
  } catch (e) {
    console.error(e)
    ElMessage.error(e.response?.data?.detail || '切换数据源失败')
  }
}

// ... 原有的 fetchData 等函数不变 ...

// 响应式数据
const symbolInput = ref('sh600519')
const currentData = ref(null)
const loading = ref(false)
const error = ref('')
const autoRefresh = ref(true)
let timer = null

// 计算属性
const statusText = ref('就绪')
const statusType = ref('info')

// 获取数据核心函数
const fetchData = async () => {
  if (!symbolInput.value) {
    ElMessage.warning('请输入股票代码')
    return
  }

  loading.value = true
  error.value = ''
  statusText.value = '加载中...'
  statusType.value = 'warning'

  try {
    // 1. 获取行情数据
    const res = await axios.get(`${API_BASE}/data/realtime/${symbolInput.value}`)
    
    if (res.data.success) {
      currentData.value = res.data.data
      
      // 【关键修复】数据获取成功后，立即刷新数据源状态！
      // 因为自动降级可能发生在这里，后端状态可能变了，必须同步
      await fetchSourceStatus() 
      
      // 现在 statusText 和 currentSourceName 已经是最新的了
      statusText.value = '数据正常'
      statusType.value = 'success'
      
      if (autoRefresh.value && !timer) {
        startTimer()
      }
    } else {
      throw new Error(res.data.message || '返回数据格式异常')
    }
  } catch (err) {
    console.error(err)
    error.value = err.message || '网络请求失败'
    statusText.value = '连接失败'
    statusType.value = 'danger'
    ElMessage.error('获取行情失败：' + error.value)
    if (timer) stopTimer()
  } finally {
    loading.value = false
  }
}

// 定时器控制
const startTimer = () => {
  if (timer) clearInterval(timer)
  timer = setInterval(() => {
    // 只在有数据且非加载状态下刷新
    if (currentData.value && !loading.value) {
      fetchData()
    }
  }, 3000) // 3秒刷新一次
}

const stopTimer = () => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

const toggleAutoRefresh = () => {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    startTimer()
    ElMessage.success('已开启自动刷新')
  } else {
    stopTimer()
    ElMessage.info('已暂停自动刷新')
  }
}

// 工具函数
const getPriceColor = (val) => {
  if (val > 0) return 'text-up'
  if (val < 0) return 'text-down'
  return 'text-flat'
}

const getPriceType = (val) => {
  if (val > 0) return 'danger' // 红
  if (val < 0) return 'success' // 绿
  return 'info'
}

const formatNumber = (num) => {
  if (num === null || num === undefined) return '--'
  return Number(num).toFixed(2)
}

const formatVolume = (num) => {
  if (num === null || num === undefined) return '--'
  const n = Number(num)
  if (n > 100000000) return (n / 100000000).toFixed(2) + '亿'
  if (n > 10000) return (n / 10000).toFixed(2) + '万'
  return n.toFixed(0)
}

// 生命周期中调用
onMounted(() => {
  fetchSourceStatus() // 先加载状态
  fetchData()         // 再加载数据
})

onUnmounted(() => {
  stopTimer()
})
</script>

<style scoped>
.market-container {
  padding: 20px;
  max-width: 1000px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
  font-size: 16px;
}

.price-card {
  margin-top: 20px;
}

.price-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.price-header h2 {
  margin: 0;
  font-size: 24px;
  color: #333;
}

.price-header small {
  color: #999;
  font-size: 14px;
  font-weight: normal;
}

.price-main {
  text-align: center;
  padding: 20px 0;
  background: #f9fafc;
  border-radius: 8px;
}

.current-price {
  font-size: 48px;
  font-weight: bold;
  margin-right: 15px;
}

.change-info {
  font-size: 24px;
  font-weight: 500;
}

/* 涨跌颜色 */
.text-up { color: #f56c6c; } /* 红 */
.text-down { color: #67c23a; } /* 绿 */
.text-flat { color: #909399; }

.stats-row {
  text-align: center;
}

.stat-label {
  color: #909399;
  font-size: 14px;
  margin-bottom: 5px;
}

.stat-value {
  font-size: 18px;
  font-weight: 500;
  color: #303133;
}

.time-text {
  font-size: 14px;
  color: #909399;
}

.alert-box {
  margin-top: 15px;
  padding: 10px;
  background: #fdf6ec;
  color: #e6a23c;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.source-control-card {
  background-color: #f5f7fa;
  border: 1px solid #e4e7ed;
}

.control-row {
  display: flex;
  align-items: center;
  font-size: 14px;
  color: #606266;
}

.label {
  font-weight: bold;
  margin-right: 10px;
}

</style>