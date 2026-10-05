<template>
  <div class="backtest-container">
    <el-row :gutter="20">
      <!-- 左侧：配置区 -->
      <el-col :span="8">
        <el-card shadow="never">
          <template #header>⚙️ 回测配置</template>
          
          <el-form label-position="top">
            <el-form-item label="股票代码">
              <el-input v-model="form.symbol" placeholder="sh600519" />
            </el-form-item>
            
            <el-form-item label="时间范围">
              <el-date-picker
                v-model="dateRange" type="daterange" range-separator="至"
                start-placeholder="开始日期" end-placeholder="结束日期"
                value-format="YYYY-MM-DD" style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="选择策略">
              <el-select v-model="selectedStrategyId" placeholder="请选择策略" style="width: 100%" @change="onStrategyChange">
                <el-option
                  v-for="item in strategies"
                  :key="item.id"
                  :label="item.name"
                  :value="item.id"
                >
                  <span style="float: left">{{ item.name }}</span>
                  <span style="float: right; color: #8492a6; font-size: 13px">{{ item.description.substring(0, 10) }}...</span>
                </el-option>
              </el-select>
              <el-alert v-if="currentStrategy" :title="currentStrategy.description" type="info" show-icon :closable="false" style="margin-top: 10px; font-size: 12px;"/>
            </el-form-item>

            <!-- 动态参数表单 -->
            <div v-if="currentStrategy && currentStrategy.params">
              <el-divider content-position="left">策略参数设置</el-divider>
              <el-form-item 
                v-for="param in currentStrategy.params" 
                :key="param.key" 
                :label="param.label"
              >
                <!-- 整数输入 -->
                <el-input-number 
                  v-if="param.type === 'int'" 
                  v-model="form.params[param.key]" 
                  :min="param.min" :max="param.max" :step="param.step" 
                  style="width: 100%"
                />
                <!-- 浮点数输入 (用滑块或数字框) -->
                <el-slider 
                  v-else-if="param.type === 'float'" 
                  v-model="form.params[param.key]" 
                  :min="param.min" :max="param.max" :step="param.step" 
                  show-input
                />
              </el-form-item>
            </div>

            <el-button type="primary" style="width: 100%; margin-top: 20px;" @click="runBacktest" :loading="loading">
              🚀 运行回测
            </el-button>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：结果展示区 (保持不变，略) -->
      <el-col :span="16">
        <!-- ... (复用之前的右侧代码，包含图表和表格) ... -->
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>📊 回测结果</span>
              <el-tag v-if="result" :type="result.total_return > 0 ? 'success' : 'danger'">
                {{ result.total_return > 0 ? '盈利' : '亏损' }} {{ result.total_return }}%
              </el-tag>
            </div>
          </template>
          <div v-if="!result" style="height: 400px; display: flex; align-items: center; justify-content: center; color: #999;">
            暂无回测结果，请点击运行
          </div>
          <div v-else>
            <el-row :gutter="20" style="margin-bottom: 20px;">
              <el-col :span="8"><el-statistic title="总收益率" :value="result.total_return" suffix="%" /></el-col>
              <el-col :span="8"><el-statistic title="最大回撤" :value="result.max_drawdown" suffix="%" /></el-col>
              <el-col :span="8"><el-statistic title="最终资产" :value="result.final_asset" prefix="¥" /></el-col>
            </el-row>
            <div ref="chartRef" style="height: 450px; width: 100%; margin-top: 20px; display: block; position: relative;"></div>
            <el-divider>交易记录 ({{ result.trades.length }}笔)</el-divider>
            <el-table :data="result.trades" style="width: 100%" height="200">
              <el-table-column prop="date" label="日期" width="120" />
              <el-table-column prop="type" label="类型" width="80">
                <template #default="scope"><el-tag :type="scope.row.type === 'buy' ? 'success' : 'warning'">{{ scope.row.type }}</el-tag></template>
              </el-table-column>
              <el-table-column prop="price" label="价格" />
              <el-table-column prop="qty" label="数量" />
            </el-table>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import * as echarts from 'echarts'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

const strategies = ref([])
const selectedStrategyId = ref('')
const form = ref({
  symbol: 'sh600519',
  params: {} // 动态参数
})
const dateRange = ref([])
const loading = ref(false)
const result = ref(null)
const chartRef = ref(null)
let myChart = null

// 辅助函数：智能判断是否为买入操作
const isBuyAction = (trade) => {
  if (!trade) return false
  const t = String(trade.type || trade.action || trade.direction || '').toUpperCase()
  
  // 匹配常见的大写/小写/中文买入标识
  return t === 'BUY' || t === 'LONG' || t === 'OPEN_LONG' || t === '买入' || t === '多'
}

// 辅助函数：智能判断是否为卖出操作
const isSellAction = (trade) => {
  if (!trade) return false
  const t = String(trade.type || trade.action || trade.direction || '').toUpperCase()
  
  // 匹配常见的大写/小写/中文卖出标识
  return t === 'SELL' || t === 'SHORT' || t === 'CLOSE_LONG' || t === 'OPEN_SHORT' || t === '卖出' || t === '空'
}

// 当前选中的策略详情
const currentStrategy = computed(() => {
  return strategies.value.find(s => s.id === selectedStrategyId.value)
})

onMounted(async () => {
  // 1. 加载策略列表
  try {
    const res = await axios.get(`${API_BASE}/backtest/strategies`)
    strategies.value = res.data
    if (strategies.value.length > 0) {
      selectedStrategyId.value = strategies.value[0].id
      initParams()
    }
  } catch (e) {
    ElMessage.error('加载策略列表失败')
  }
  
  // 默认时间
  const end = new Date()
  const start = new Date()
  start.setFullYear(start.getFullYear() - 1)
  dateRange.value = [start.toISOString().split('T')[0], end.toISOString().split('T')[0]]
  
  // 初始化图表
  await nextTick()
  if (chartRef.value) myChart = echarts.init(chartRef.value)
  window.addEventListener('resize', () => myChart && myChart.resize())
})

// 策略切换时，重置参数为默认值
const onStrategyChange = () => {
  initParams()
}

const initParams = () => {
  if (!currentStrategy.value) return
  const defaults = {}
  currentStrategy.value.params.forEach(p => {
    defaults[p.key] = p.default
  })
  form.value.params = defaults
}

const runBacktest = async () => {
  // 1. 基础验证
  if (!selectedStrategyId.value) {
    ElMessage.warning('请选择策略')
    return
  }
  if (!dateRange.value || dateRange.value.length !== 2) {
    ElMessage.warning('请选择时间范围')
    return
  }
  
  loading.value = true
  try {
    // 2. 发送请求
    console.log('🚀 [API] 开始发送回测请求...')
    const res = await axios.post(`${API_BASE}/backtest/run`, {
      symbol: form.value.symbol,
      start_date: dateRange.value[0],
      end_date: dateRange.value[1],
      strategy_id: selectedStrategyId.value,
      params: form.value.params
    })
    
    // 3. 接收数据
    result.value = res.data.data
    ElMessage.success('回测完成!')
    
    console.log('📊 [调试] 回测数据已接收:', result.value)
    console.log('📊 [调试] 资金曲线长度:', result.value.capital_curve?.length)
    console.log('📊 [调试] 交易记录长度:', result.value.trades?.length)
    
    // 4. 等待 DOM 更新
    await nextTick()
    
    // 5. 检查 DOM 元素
    console.log('🔍 [调试] chartRef.value:', chartRef.value)
    
    if (!chartRef.value) {
      console.error('❌ 致命错误：图表容器 DOM (chartRef) 不存在！请检查模板中是否有 v-if 控制了该 div。')
      ElMessage.error('图表容器未找到，请检查页面布局')
      return
    }
    
    // 6. 检查/重建 ECharts 实例
    console.log('🔍 [调试] 当前 myChart 实例:', myChart)
    
    if (!myChart) {
      console.warn('⚠️ 警告：myChart 实例为空，正在重新初始化...')
      
      // 强制指定 canvas 渲染器，避免 SVG 在某些情况下的兼容性问题
      myChart = echarts.init(chartRef.value, null, { 
        renderer: 'canvas',
        width: 'auto',
        height: 'auto'
      })
      
      console.log('✅ [调试] ECharts 重新初始化成功，实例 ID:', myChart.id)
      
      // 重新绑定窗口缩放事件
      window.addEventListener('resize', () => {
        if (myChart) myChart.resize()
      })
    }
    
    // 7. 检查容器实际尺寸 (关键步骤)
    const rect = chartRef.value.getBoundingClientRect()
    console.log(`📏 [调试] 容器实际物理尺寸：宽=${rect.width.toFixed(2)}px, 高=${rect.height.toFixed(2)}px`)
    
    if (rect.height === 0 || rect.width === 0) {
      console.error('❌ 致命错误：图表容器尺寸为 0！可能是 CSS 高度塌陷或被父元素隐藏。')
      ElMessage.error('图表区域高度为 0，请检查 CSS 样式或父级元素 display 属性')
      return
    }
    
    // 8. 执行绘图
    console.log('🎨 [调试] 准备调用 drawChart...')
    
    // 传入数据、交易记录和基准曲线
    drawChart(
      result.value.capital_curve, 
      result.value.trades,
      result.value.benchmark_curve || []
    )
    
    console.log('✅ [调试] runBacktest 流程全部结束')
    
  } catch (e) {
    console.error('❌ [API] 回测请求失败:', e)
    const msg = e.response?.data?.detail || e.message || '未知错误'
    ElMessage.error('回测失败：' + msg)
  } finally {
    loading.value = false
  }
}
// frontend/src/views/BacktestView.vue 中的 drawChart 函数
// data: 策略资金曲线
// trades: 交易记录
// benchmark: 基准（买入并持有）资金曲线
const drawChart = (data, trades, benchmark) => {
  if (!myChart) {
    console.error('❌ ECharts 实例不存在')
    return
  }

  if (!data || data.length === 0) {
    console.warn('⚠️ 数据为空，清除图表')
    myChart.clear()
    return
  }

  // 1. 数据预处理
  const dates = data.map(item => item.date)
  const assets = data.map(item => item.asset)

  // 基准曲线
  const hasBenchmark = benchmark && Array.isArray(benchmark) && benchmark.length > 0
  const benchmarkAssets = hasBenchmark ? benchmark.map(item => item.asset) : []
  
  // 计算最大最小值用于 Y 轴留白
  const maxAsset = Math.max(...assets)
  const minAsset = Math.min(...assets)
  const range = maxAsset - minAsset

  // 2. 处理买卖点标记 (MarkPoints)
  // 将交易记录转换为 ECharts 需要的 format
  const buyPoints = []
  const sellPoints = []

  if (trades && Array.isArray(trades)) {
    trades.forEach(trade => {
      // 1. 获取时间 (兼容多种字段名)
      const timeKey = trade.entry_time || trade.exit_time || trade.time || trade.date
      if (!timeKey) return 

      // 2. 查找对应的日期索引
      const index = dates.findIndex(d => {
        const tStr = String(timeKey).split(' ')[0] 
        return d === tStr || String(d).startsWith(tStr)
      })

      if (index !== -1) {
        const assetAtTrade = assets[index]
        
        // 🛠️ 关键修复：使用辅助函数判断类型
        const isBuy = isBuyAction(trade)
        const isSell = isSellAction(trade)
        
        // 如果既不是买也不是卖，可能是平多/平空等复杂操作，根据价格变化或默认逻辑处理
        // 这里我们简单处理：如果是 buy 标记为买，否则默认为卖 (或者你可以跳过未知类型)
        const displayType = isBuy ? 'BUY' : 'SELL' 
        const displayName = isBuy ? '买入' : '卖出'
        const displayColor = isBuy ? '#ef476f' : '#06d6a0' // 红买绿卖
        const displaySymbol = isBuy ? 'pin' : 'arrow'

        const pointConfig = {
          name: displayName,
          coord: [dates[index], assetAtTrade],
          value: `${displayName}\n${trade.price?.toFixed(2) || ''}`,
          itemStyle: { color: displayColor },
          symbol: displaySymbol,
          symbolSize: isBuy ? 14 : 12,
        }

        if (isBuy) {
          buyPoints.push(pointConfig)
        } else {
          // 只有确认为卖出或其他非买入操作才放入卖出队列
          // 防止未知类型污染数据，可以加个 console.log 观察
          if (!isBuy) sellPoints.push(pointConfig)
        }
      }
    })
  }

  const gradientColor = new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: 'rgba(64, 158, 255, 0.5)' },
    { offset: 1, color: 'rgba(64, 158, 255, 0.01)' }
  ])

  const option = {
    backgroundColor: '#ffffff',
    title: { text: '资金权益曲线', left: 'center', top: 10, textStyle: { color: '#333', fontSize: 16, fontWeight: 'bold' } },
    
    // 🛠️ 修复重点：Tooltip Formatter
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: 'rgba(255, 255, 255, 0.9)',
      borderColor: '#eee',
      borderWidth: 1,
      textStyle: { color: '#333' },
      formatter: (params) => {
        if (!params || params.length === 0) return ''
        const date = params[0].name // X 轴日期
        
        let html = `<div style="font-weight:bold; margin-bottom:5px;">${date}</div>`

        // 多条曲线信息（策略 & 基准）
        params.forEach(p => {
          const val = Number(p.value).toFixed(2)
          const seriesName = p.seriesName || '总资产'
          html += `<div>${seriesName}: <span style="color:${p.color}; font-weight:bold;">${val}</span></div>`
        })
        
        // 🛡️ 安全过滤交易记录
        if (trades && Array.isArray(trades)) {
          const dayTrades = trades.filter(t => {
            // 获取交易时间，兼容多种字段名
            const tTime = t.entry_time || t.exit_time || t.time || t.date
            if (!tTime) return false
            
            // 转为字符串并截取日期部分 (防止 "2023-01-01 10:00:00" 这种格式)
            const tDateStr = String(tTime).split(' ')[0]
            
            // 比较日期
            return tDateStr === date || String(date).startsWith(tDateStr)
          })

          if (dayTrades.length > 0) {
            html += `<div style="margin-top:5px; border-top:1px solid #eee; padding-top:5px;">`
            dayTrades.forEach(t => {
              // 🛠️ 关键修复：使用辅助函数
              const isBuy = isBuyAction(t)
              const color = isBuy ? '#ef476f' : '#06d6a0'
              const label = isBuy ? '🟢 买入' : '🔴 卖出'
              const price = t.price ? Number(t.price).toFixed(2) : '-'
              
              html += `<div style="font-size:12px; color:${color}">
                ${label} @ ${price}
              </div>`
            })
            html += `</div>`
          }
        }
        return html
      }
    },
    
    grid: { left: '5%', right: '5%', bottom: '15%', top: '15%', containLabel: true },
    xAxis: { type: 'category', data: dates, boundaryGap: false, axisLine: { lineStyle: { color: '#ddd' } }, axisLabel: { color: '#666' } },
    yAxis: { 
      type: 'value', 
      scale: true, 
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
      axisLabel: { formatter: (v) => v.toLocaleString(), color: '#666' }
    },
    dataZoom: [{ type: 'slider', show: true, xAxisIndex: [0], start: 0, end: 100, bottom: 10, height: 20 }, { type: 'inside', xAxisIndex: [0], start: 0, end: 100 }],
    series: [
      {
        name: '策略总资产',
        type: 'line',
        data: assets,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 3, color: '#409EFF', shadowColor: 'rgba(64, 158, 255, 0.3)', shadowBlur: 10, shadowOffsetY: 5 },
        areaStyle: { color: gradientColor },
        markPoint: {
          silent: true,
          data: [...buyPoints, ...sellPoints],
          label: { show: true, position: 'inside', color: '#000000', fontSize: 10, formatter: '{b}' }//这里调整收益图中标签的字体颜色
        }
      },
      ...(hasBenchmark
        ? [
            {
              name: '基准买入持有',
              type: 'line',
              data: benchmarkAssets,
              smooth: true,
              symbol: 'none',
              lineStyle: {
                width: 2,
                color: '#F5A623',
                type: 'dashed'
              },
              areaStyle: { opacity: 0 } // 基准不填充面积，只画线
            }
          ]
        : [])
    ]
  }

  try {
    myChart.setOption(option, { notMerge: false, lazyUpdate: false })
    console.log('✅ 图表渲染成功 (高级版)')
    
    // 🛠️ 修复 resize 警告：使用 setTimeout 脱离主进程
    setTimeout(() => {
      if (myChart) {
        myChart.resize()
        console.log('📏 图表 resize 完成')
      }
    }, 0) 
    
  } catch (e) {
    console.error('❌ 图表渲染失败:', e)
  }
}

</script>

<style scoped>
.backtest-container { padding: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>