<template>
  <el-container style="height: 100vh; background-color: #f0f2f5;">
    <el-header style="background-color: #409EFF; color: white; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
      <div style="display: flex; align-items: center;">
        <h2 style="margin: 0; font-size: 20px; font-weight: bold;">📊 QuantTrade Pro</h2>
        
        <!-- 新增：顶部导航菜单 -->
        <el-menu 
          mode="horizontal" 
          router 
          :default-active="$route.path"
          style="border: none; background: transparent; margin-left: 40px; flex: 1;"
          text-color="#fff"
          active-text-color="#ffd04b"
        >
          <el-menu-item index="/">🏠 首页</el-menu-item>
          <el-menu-item index="/market">📈 行情监控</el-menu-item>
          <el-menu-item index="/backtest">🧪 回测中心</el-menu-item>
          <!-- 未来可以加： <el-menu-item index="/trade">💼 模拟交易</el-menu-item> -->
        </el-menu>
      </div>

      <div style="font-size: 14px; opacity: 0.9;">
        {{ currentTime }}
      </div>
    </el-header>
    
    <el-main style="padding: 20px; overflow-y: auto;">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const currentTime = ref('')
let timer = null

const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleString('zh-CN', { hour12: false })
}

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style>
body { margin: 0; font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif; }
.el-header { height: 60px !important; }
</style>