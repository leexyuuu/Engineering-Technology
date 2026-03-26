Page({
  data: {
    userInfo: {},
    isAdmin: false
  },

  onShow() {
    const userInfo = wx.getStorageSync('userInfo');
    if (userInfo) {
      // 如果没有头像，设置默认头像
      if (!userInfo.avatarUrl) {
        userInfo.avatarUrl = '/images/default-avatar.png';
      }
      this.setData({
        userInfo: userInfo,
        isAdmin: userInfo.role === 1 // 修改为数字比较
      });
    } else {
      wx.redirectTo({
        url: '/pages/register/register'
      });
    }
  },

  onNickNameReview(e) {
    // 更新本地存储的用户信息
    const userInfo = this.data.userInfo;
    userInfo.nickName = e.detail.nickname;
    wx.setStorageSync('userInfo', userInfo);
    this.setData({
      userInfo: userInfo
    });
  },

  async onChooseAvatar(e) {
    const { avatarUrl } = e.detail;

    try {
      wx.showLoading({
        title: '更新中...',
        mask: true
      });

      // 先将临时文件上传到云存储
      const cloudPath = `avatars/${this.data.userInfo.teacherId}_${Date.now()}.jpg`;
      const uploadResult = await wx.cloud.uploadFile({
        cloudPath: cloudPath,
        filePath: avatarUrl
      });

      if (!uploadResult.fileID) {
        throw new Error('上传头像失败');
      }

      // 调用云函数更新用户信息，保存云存储的文件ID
      const result = await wx.cloud.callFunction({
        name: 'updateUser',
        data: {
          teacherId: this.data.userInfo.teacherId,
          updateData: {
            avatarUrl: uploadResult.fileID  // 保存云文件ID而不是临时路径
          }
        }
      });

      if (result.result && result.result.code === 0) {
        // 更新本地存储的用户信息
        const userInfo = this.data.userInfo;
        userInfo.avatarUrl = uploadResult.fileID;
        wx.setStorageSync('userInfo', userInfo);

        // 更新页面显示
        this.setData({
          userInfo
        });

        wx.showToast({
          title: '更新成功',
          icon: 'success'
        });
      } else {
        throw new Error('更新失败');
      }
    } catch (err) {
      console.error('更新头像失败：', err);
      wx.showToast({
        title: '更新失败',
        icon: 'error'
      });
    } finally {
      wx.hideLoading();
    }
  },

  handleLogout() {
    wx.showModal({
      title: '提示',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          // 获取 app 实例并清除步数数据缓存
          const app = getApp();
          app.clearWeRunData();
          
          // 清除本地存储的用户信息
          wx.removeStorageSync('userInfo');
          
          // 跳转到登录页面
          wx.reLaunch({
            url: '/pages/register/register'
          });
        }
      }
    });
  },

  // 管理员导出数据
  onExportData() {
    wx.navigateTo({
      url: '/pages/export/export'
    });
  },

  async onExportExcel() {
    wx.showLoading({ title: '导出中...' });
    try {
      const now = new Date();
      const year = now.getFullYear();
      const month = now.getMonth() + 1;
      const res = await wx.cloud.callFunction({
        name: 'exportStepStatistics',
        data: { year, month }
      });
      if (res.result && res.result.code === 0) {
        // 获取临时下载链接
        const fileRes = await wx.cloud.getTempFileURL({
          fileList: [res.result.fileID]
        });
        const url = fileRes.fileList[0].tempFileURL;
        wx.setClipboardData({
          data: url,
          success: () => {
            wx.showToast({ title: '下载链接已复制', icon: 'success' });
          }
        });
      } else {
        wx.showToast({ title: '导出失败', icon: 'error' });
      }
    } catch (e) {
      wx.showToast({ title: '导出异常', icon: 'error' });
    } finally {
      wx.hideLoading();
    }
  }
}); 