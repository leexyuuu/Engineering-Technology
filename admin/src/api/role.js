import request from '@/utils/request'
const { asyncRoutes, constantRoutes } = require('../../mock/role/routes.js')
const { deepClone } = require('../../mock/utils.js')
const routes = deepClone([...constantRoutes, ...asyncRoutes])

export function getRoutes() {
  return {
    code: 20000,
    data: routes
  }
}

export function getRoles() {
  return request({
    url: '/api/admin/role/list',
    method: 'get'
  })
}

export function addRole(data) {
  return request({
    url: '/api/admin/role',
    method: 'post',
    data
  })
}

export function updateRole(id, data) {
  return request({
    url: `/api/admin/role/${id}`,
    method: 'put',
    data
  })
}

export function deleteRole(id) {
  return request({
    url: `/api/admin/role/${id}`,
    method: 'delete'
  })
}
