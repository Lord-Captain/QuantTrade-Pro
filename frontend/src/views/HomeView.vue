<template>
  <div style="text-align: center; padding: 50px; color: #606266;">
    <h1 style="font-size: 32px; margin-bottom: 20px;">🚀 欢迎使用 QuantTrade Pro</h1>
    <p style="font-size: 18px;">请选择上方菜单进入功能模块</p>
    <div style="margin-top: 40px;">
      <el-button type="primary" size="large" @click="$router.push('/market')">📈 去行情监控</el-button>
      <el-button type="success" size="large" @click="$router.push('/backtest')" style="margin-left: 20px;">🧪 去回测中心</el-button>
    </div>
  </div>
</template>

<script setup>
// 无需额外逻辑
</script>