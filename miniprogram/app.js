// app.js
App({
  globalData: {
    apiBaseUrl: 'https://your-api-domain',  // API基础地址
    isRealHide: false,  // 标记是否真正退出小程序
    weRunData: null,  // 存储步数数据
    weRunDataTeacherId: null  // 存储步数数据所属的用户ID
  },

  // 清除步数数据缓存
  clearWeRunData() {
    this.globalData.weRunData = null;
    this.globalData.weRunDataTeacherId = null;
  },

  // 设置步数数据（同时记录用户ID）
  setWeRunData(data, teacherId) {
    this.globalData.weRunData = data;
    this.globalData.weRunDataTeacherId = teacherId;
  },

  // 获取步数数据
  getWeRunData() {
    return this.globalData.weRunData;
  },

  // 检查步数数据是否属于指定用户
  isWeRunDataForUser(teacherId) {
    return this.globalData.weRunDataTeacherId === teacherId;
  },

  onLaunch() {
    if (!wx.cloud) {
      console.error("请使用 2.2.3 或以上的基础库以使用云能力");
    } else {
      wx.cloud.init({
        // env 参数说明：
        //   env 参数决定接下来小程序发起的云开发调用（wx.cloud.xxx）会默认请求到哪个云环境的资源
        //   此处请填入环境 ID, 环境 ID 可打开云控制台查看
        //   如不填则使用默认环境（第一个创建的环境）
        env: "cloudbase-6gmvgpa8e66afee4",
        traceUser: true,
      });
    }

    const userInfo = wx.getStorageSync('userInfo');
    if (!userInfo) {
      wx.redirectTo({
        url: '/pages/register/register'
      });
    }
  },

  onHide() {
    this.globalData.isRealHide = true;
  },

  onShow() {
    this.globalData.isRealHide = false;
  },

  onError(err) {
    // 监控错误
    console.error('App Error:', err);
  },
});
