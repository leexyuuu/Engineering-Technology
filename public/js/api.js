/** 请求封装：自动携带 token，401 自动跳转登录页 */
window.API = {
  get token() { return localStorage.getItem('bx_token') || ''; },
  set token(v) { v ? localStorage.setItem('bx_token', v) : localStorage.removeItem('bx_token'); },

  async req(method, url, body) {
    const headers = {};
    if (this.token) headers.Authorization = 'Bearer ' + this.token;
    let payload;
    if (body instanceof FormData) {
      payload = body;
    } else if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
      payload = JSON.stringify(body);
    }
    let res;
    try {
      res = await fetch(url, { method, headers, body: payload });
    } catch (e) {
      throw new Error('网络连接失败，请检查服务是否启动');
    }
    let json = null;
    try { json = await res.json(); } catch (e) { /* 空响应 */ }
    if (res.status === 401) {
      this.token = '';
      Store.user = null;
      if (location.hash !== '#/login') location.hash = '#/login';
      throw new Error((json && json.message) || '登录已过期，请重新登录');
    }
    if (!res.ok) throw new Error((json && json.message) || '请求失败（' + res.status + '）');
    return json ? json.data : null;
  },

  get: function (u) { return API.req('GET', u); },
  post: function (u, b) { return API.req('POST', u, b); },
  put: function (u, b) { return API.req('PUT', u, b); },
  del: function (u) { return API.req('DELETE', u); },
  upload: function (form) { return API.req('POST', '/api/attachments', form); },
};
