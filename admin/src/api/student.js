import request from '@/utils/request'

// 学生相关API
export function fetchStudentList(data) {
  return request({
    url: '/api/studentslist',
    method: 'get',
    params:data
  })
}

export function fetchStudent(id) {
  return request({
    url: `/api/students/${id}`,
    method: 'get'
  })
}

export function createStudent(data) {
  return request({
    url: '/api/students/create',
    method: 'post',
    params:data
  })
}

export function updateStudent(id, data) {
  return request({
    url: `/api/students/${id}`,
    method: 'put',
    params:data
  })
}

export function deleteStudent(id) {
  return request({
    url: `/api/students/${id}`,
    method: 'delete'
  })
} 