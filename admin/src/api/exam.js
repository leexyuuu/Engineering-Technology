import request from '@/utils/request'

// 考试相关API
export function fetchExamList(params) {
  return request({
    url: '/api/exam/list',
    method: 'get',
    params
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
    data
  })
}

export function updateExam(id, data) {
  return request({
    url: `/api/exam/${id}`,
    method: 'put',
    data
  })
}

export function deleteExam(id) {
  return request({
    url: `/api/exam/${id}`,
    method: 'delete'
  })
}

// 学生相关API
export function fetchExamStudentList(exam_id, params) {
  return request({
    url: `/api/exam/${exam_id}/students`,
    method: 'get',
    params
  })
}

export function createExamStudent(exam_id, data) {
  return request({
    url: `/api/exam/${exam_id}/students`,
    method: 'post',
    data
  })
}

export function updateExamStudent(exam_id, student_id, data) {
  return request({
    url: `/api/exam/${exam_id}/students/${student_id}`,
    method: 'put',
    data
  })
}

export function deleteExamStudent(exam_id, student_id) {
  return request({
    url: `/api/exam/${exam_id}/students/${student_id}`,
    method: 'delete'
  })
}

// 题目相关API
export function fetchExamQuestionList(exam_id, params) {
  return request({
    url: `/api/exam/${exam_id}/questions`,
    method: 'get',
    params
  })
}

export function fetchExamQuestion(exam_id, question_id) {
  return request({
    url: `/api/exam/${exam_id}/questions/${question_id}`,
    method: 'get'
  })
}

export function createExamQuestion(exam_id, data) {
  return request({
    url: `/api/exam/${exam_id}/questions`,
    method: 'post',
    data
  })
}

export function updateExamQuestion(exam_id, question_id, data) {
  return request({
    url: `/api/exam/${exam_id}/questions/${question_id}`,
    method: 'put',
    data
  })
}

export function deleteExamQuestion(exam_id, question_id) {
  return request({
    url: `/api/exam/${exam_id}/questions/${question_id}`,
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
    data
  })
}

export function updateQuestionProblem(exam_id, question_id, problem_id, data) {
  return request({
    url: `/api/exam/${exam_id}/questions/${question_id}/problems/${problem_id}`,
    method: 'put',
    data
  })
}

export function deleteQuestionProblem(exam_id, question_id, problem_id) {
  return request({
    url: `/api/exam/${exam_id}/questions/${question_id}/problems/${problem_id}`,
    method: 'delete'
  })
} 