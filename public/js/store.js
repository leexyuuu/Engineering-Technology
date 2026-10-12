/** 全局状态：当前用户、未读消息数 */
window.Store = Vue.reactive({
  user: null,
  unread: 0,
});

/** 启动时恢复登录态 */
async function initStore() {
  if (!API.token) return;
  try {
    const d = await API.get('/api/auth/me');
    Store.user = d.user;
    fetchUnread();
    setInterval(fetchUnread, 30000);
  } catch (e) { /* token 失效由 API 统一处理 */ }
}

async function fetchUnread() {
  if (!Store.user) return;
  try {
    const d = await API.get('/api/notifications/unread-count');
    Store.unread = d.count;
  } catch (e) { /* 静默 */ }
}
