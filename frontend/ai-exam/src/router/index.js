import { createRouter, createWebHistory } from 'vue-router'
import LoginPage from '../components/LoginPage.vue'
import ExamPage from '../components/ExamPage.vue'

const routes = [
  {
    path: '/',
    name: 'Login',
    component: LoginPage
  },
  {
    path: '/exam',
    name: 'Exam',
    component: ExamPage
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router 