import request from '@/utils/request'

export function searchArticle(query) {
  return request({
    url: '/api/article/search/',
    method: 'get',
    params: query
  })
}

export function fetchArticle(id) {
  return request({
    url: '/api/article/'+id,
    method: 'get'
  })
}


export function createArticle(data) {
  return request({
    url: '/api/article/create',
    method: 'post',
    params:data
  })
}

export function updateArticle(data) {
  return request({
    url: '/api/article/update',
    method: 'put',
    params:data
  })
}
