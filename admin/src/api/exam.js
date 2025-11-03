import request from '@/utils/request'
import axios from 'axios'
import { getToken } from '@/utils/auth'

// 考试相关API
export function fetchExamList(data) {
  return request({
    url: '/api/exam/list',
    method: 'get',
    params: data
  })
}

export function fetchExam(id) {
  return request({
    url: `/api/exam/${id}`,
    method: 'get'
  })
}

export function createExam(data) {
  return request({
    url: '/api/exam/create',
    method: 'post',
    params: data
  })
}

export function updateExam(id, data) {
  return request({
    url: `/api/exam/${id}`,
    method: 'put',
    params: data
  })
}

export function deleteExam(id) {
  return request({
    url: `/api/exam/${id}`,
    method: 'delete'
  })
}

// 学生相关API
export function fetchExamStudentList(exam_id, data) {
  return request({
    url: `/api/exam/${exam_id}/students`,
    method: 'get',
    params: data
  })
}

export function createExamStudent(exam_id, data) {
  return request({
    url: `/api/exam/${exam_id}/students`,
    method: 'post',
    params: data
  })
}

export function updateExamStudent(exam_id, student_id, data) {
  return request({
    url: `/api/exam/${exam_id}/students/${student_id}`,
    method: 'put',
    params: data
  })
}

export function deleteExamStudent(exam_id, student_id) {
  return request({
    url: `/api/exam/${exam_id}/students/${student_id}`,
    method: 'delete'
  })
}

// 题目相关API
export function fetchExamQuestionList(exam_id) {
  return request({
    url: `/api/exam/${exam_id}/questions`,
    method: 'get'
  })
}

export function fetchExamQuestion(exam_id, question_id) {
  return request({
    url: `/api/exam/questions/${question_id}`,
    method: 'get'
  })
}

export function createExamQuestion(data) {
  return request({
    url: '/api/exam/questions/create',
    method: 'post',
    params: data
  })
}

export function updateExamQuestion(question_id, data) {
  return request({
    url: `/api/exam/questions/${question_id}`,
    method: 'put',
    params: data
  })
}

export function deleteExamQuestion(question_id) {
  return request({
    url: `/api/exam/questions/${question_id}`,
    method: 'delete'
  })
}

// 问题（小题）相关API
export function fetchQuestionProblems(exam_id, question_id) {
  return request({
    url: `/api/exam/${exam_id}/questions/${question_id}/problems`,
    method: 'get'
  })
}

export function createQuestionProblem(exam_id, question_id, data) {
  return request({
    url: `/api/exam/${exam_id}/questions/${question_id}/problems`,
    method: 'post',
    params: data
  })
}

export function updateQuestionProblem(exam_id, question_id, problem_id, data) {
  return request({
    url: `/api/exam/${exam_id}/questions/${question_id}/problems/${problem_id}`,
    method: 'put',
    params: data
  })
}

export function deleteQuestionProblem(exam_id, question_id, problem_id) {
  return request({
    url: `/api/exam/${exam_id}/questions/${question_id}/problems/${problem_id}`,
    method: 'delete'
  })
}

// 获取学生考试详情
export function fetchStudentExamResult(exam_id, student_id) {
  return request({
    url: `/api/student/exams/${exam_id}/result/${student_id}`,
    method: 'get'
  })
}

// 文件上传API
export function uploadFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/api/exam/upload-file',
    method: 'post',
    params: formData
  })
}

// 导入学生到考试API
export function importStudentsToExam(data) {
  return request({
    url: '/api/exam/import-students',
    method: 'post',
    params: data
  })
}

// 下载学生考试文件API
export function downloadStudentFiles(exam_id, student_id) {
  const token = getToken() || ''

  return axios({
    url: `/api/exam/${exam_id}/student/${student_id}/download-files`,
    method: 'get',
    responseType: 'blob', // 重要：设置响应类型为blob，用于下载文件
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }).then(response => {
    // 检查是否是错误响应（错误时后端可能返回JSON格式的错误信息）
    const contentType = response.headers['content-type']
    if (contentType && contentType.includes('application/json')) {
      // 错误响应，需要解析JSON
      return new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => {
          try {
            const errorData = JSON.parse(reader.result)
            reject(new Error(errorData.detail || errorData.message || '下载失败'))
          } catch (e) {
            reject(new Error('下载失败'))
          }
        }
        reader.onerror = () => reject(new Error('读取错误响应失败'))
        reader.readAsText(response.data)
      })
    }

    // 从响应头中获取文件名
    const contentDisposition = response.headers['content-disposition']
    let filename = `考试文件_${exam_id}_${student_id}.zip`

    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename\*=UTF-8''(.+)/i)
      if (filenameMatch) {
        filename = decodeURIComponent(filenameMatch[1])
      } else {
        const filenameMatch2 = contentDisposition.match(/filename="?(.+)"?/i)
        if (filenameMatch2) {
          filename = filenameMatch2[1]
        }
      }
    }

    // 创建blob对象并触发下载
    const blob = new Blob([response.data], { type: 'application/zip' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    return Promise.resolve()
  }).catch(error => {
    // 处理错误响应（可能是blob格式的错误JSON）
    if (error.response && error.response.data) {
      const blob = error.response.data
      if (blob instanceof Blob) {
        return new Promise((resolve, reject) => {
          const reader = new FileReader()
          reader.onload = () => {
            try {
              const errorData = JSON.parse(reader.result)
              reject(new Error(errorData.detail || errorData.message || '下载失败'))
            } catch (e) {
              reject(new Error(error.message || '下载失败'))
            }
          }
          reader.onerror = () => reject(new Error(error.message || '下载失败'))
          reader.readAsText(blob)
        })
      }
    }
    return Promise.reject(error)
  })
}
