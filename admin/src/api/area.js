import request from '@/utils/request'

export function fetchAreaList(query) {
  return request({
    url: '/api/area/list/',
    method: 'get',
    params: query
  })
}

export function fetchArea(id) {
  return request({
    url: '/api/area/'+id,
    method: 'get'
  })
}
export function searchArea(name) {
  return request({
    url: '/api/area/search/',
    method: 'get',
    params: { name }
  })
}


export function createArea(data) {
  return request({
    url: '/api/area/create',
    method: 'post',
    params:data
  })
}

export function updateArea(data) {
  return request({
    url: '/api/area/update',
    method: 'put',
    params:data
  })
}
