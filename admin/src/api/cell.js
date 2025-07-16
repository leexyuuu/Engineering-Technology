import request from '@/utils/request'

export function fetchCellList(query) {
  return request({
    url: '/api/cell/list/',
    method: 'get',
    params: query
  })
}
export function searchCell(data) {
  return request({
    url: '/api/cell/search/',
    method: 'get',
    params: data
  })
}


export function fetchCell(id) {
  return request({
    url: '/api/cell/'+id,
    method: 'get'
  })
}


export function createCell(data) {
  return request({
    url: '/api/cell/create',
    method: 'post',
    params: data})
  }
export function updateCell(data) {
  return request({
    url: '/api/cell/update',
    method: 'put',
    params: data
  })
}
