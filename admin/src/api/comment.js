import request from '@/utils/request'

export function fetchList(query) {
  return request({
    url: '/api/comment/search/',
    method: 'get',
    params: query
  })
}

export function fetchComment(id) {
  return request({
    url: '/api/comment/'+id,
    method: 'get'
  })
}

export function searchComment(name) {
  return request({
    url: '/api/comment/search/',
    method: 'get',
    params: { name }
  })
}

export function createComment(data) {
  return request({
    url: '/api/comment/create',
    method: 'post',
    params:data
  })
}

export function updateComment(data) {
  return request({
    url: '/api/comment/update',
    method: 'put',
    params:data
  })
}

export function deleteComment(id) {
  return request({
    url: `/api/comment/${id}`,
    method: 'delete'
  })
}
