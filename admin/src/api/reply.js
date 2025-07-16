import request from '@/utils/request'

export function fetchList(query) {
  return request({
    url: '/api/reply/search/',
    method: 'get',
    params: query
  })
}

export function fetchReply(id) {
  return request({
    url: '/api/reply/'+id,
    method: 'get'
  })
}

export function searchReply(name) {
  return request({
    url: '/api/reply/search/',
    method: 'get',
    params: { name }
  })
}

export function createReply(data) {
  return request({
    url: '/api/reply/create',
    method: 'post',
    params:data
  })
}

export function updateReply(data) {
  return request({
    url: '/api/reply/update',
    method: 'put',
    params:data
  })
}

export function deleteReply(id) {
  return request({
    url: `/api/reply/${id}`,
    method: 'delete'
  })
}
