import { createRouter, createWebHistory } from 'vue-router'
import MarketView from '../views/MarketView.vue'
import BacktestView from '../views/BacktestView.vue'
import HomeView from '../views/HomeView.vue' // 引入新组件

const routes = [
  { path: '/', name: 'Home', component: HomeView }, // 直接使用组件
  { path: '/market', name: 'Market', component: MarketView },
  { path: '/backtest', name: 'Backtest', component: BacktestView }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router