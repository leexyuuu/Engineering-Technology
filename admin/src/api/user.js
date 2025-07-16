import request from '@/utils/request'
import qs from 'qs'
export function login(data) {
  return request({
    url: '/api/admin/token',
    method: 'post',
    params:  {username: data.username,password: data.password}
  })
}

export function getInfo(token) {
  return request({
    url: '/api/admin/me',
    method: 'get',
    params: { token }
  })
}
export function fetchUser(id) {
  return request({
    url: '/api/admin/users/'+id,
    method: 'get'
  })
}

export function logout() {
  return request({
    url: '/api/admin/logout',
    method: 'post'
  })
}

export function searchUser(data) {
  return request({
    url: '/api/user/search/',
    method: 'get',
    params: data
  })
}

export function mockUsers() {
  return request({
    url: '/api/admin/mockusers/',
    method: 'get',
  })
}
export function addMockuser(data) {
  return request({
    url: '/api/admin/addmockuser',
    method: 'post',
    params: data
  })
}

export function updateUser(data) {
  return request({
    url: '/api/users/update',
    method: 'put',
    params: data
  })
}

