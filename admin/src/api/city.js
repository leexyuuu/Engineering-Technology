import request from '@/utils/request'
import qs from 'qs';

export function fetchCityList(query) {
  return request({
    url: '/api/city/list/',
    method: 'get',
    params: query
  })
}

export function fetchCity(id) {
  return request({
    url: '/api/city/'+id,
    method: 'get'
  })
}

export function searchCity(name) {
  return request({
    url: '/api/city/search/',
    method: 'get',
    params: { name }
  })
}


export function createCity(data) {
  return request({
   url:'/api/city/create',
   method: 'post',
   params: data})
}

export function updateCity(data) {
  return request({
    url: '/api/city/update',
    method: 'put',
    params: data
  })
}
