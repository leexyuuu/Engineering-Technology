import { createRouter, createWebHistory } from 'vue-router'
import LoginPage from '../components/LoginPage.vue'
import ExamPage from '../components/ExamPage.vue'
import RegisterPage from '../components/RegisterPage.vue'
import ChoiceExamPage from '../components/ChoiceExamPage.vue'

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
    path: '/exam',
    name: 'Exam',
    component: ExamPage
  },
  {
    path: '/choice-exam',
    name: 'ChoiceExam',
    component: ChoiceExamPage
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router 