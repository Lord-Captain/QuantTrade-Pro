// src/main.js
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router' // <--- 关键：引入 router

const app = createApp(App)

app.use(ElementPlus)
app.use(router) // <--- 关键：必须 use(router) 才能注册 router-view 组件

app.mount('#app')