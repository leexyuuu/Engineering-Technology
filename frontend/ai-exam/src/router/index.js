import { createRouter, createWebHistory } from 'vue-router'
import LoginPage from '../components/LoginPage.vue'
import ExamPage from '../components/ExamPage.vue'
import RegisterPage from '../components/RegisterPage.vue'
import ExamNotice from '../components/ExamNotice.vue'

const routes = [
  {
    path: '/',
    name: 'Login',
    component: LoginPage
  },
  {
    path: '/register',
    name: 'Register',
    component: RegisterPage
  },
  {
    path: '/exam-notice',
    name: 'ExamNotice',
    component: ExamNotice
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