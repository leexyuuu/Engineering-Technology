// index.js
const app = getApp();

Page({
  data: {
    todaySteps: 0,
    targetSteps: 7000,
    progressRotation: -180, // 进度条旋转角度
    rank: 1,
    calories: 0,
    totalSteps: 0,
    totalDistance: 0,
    totalCalories: 0,
    monthlyAchievedDays: 0, // 本月达标天数
    currentDate: '2025-01',
    weekDay: '1/8 周三',
    dailySteps: 0,
    dailyDistance: 0,
    recordList: [],
    avatarUrl: '',
    syncStatus: 'loading' // 同步状态：loading, success, error
  },

  onShow() {
    // 获取用户信息
    const userInfo = wx.getStorageSync('userInfo');
    
    if (userInfo && userInfo.teacherId) {
      // 检查用户是否切换
      if (this.lastTeacherId && this.lastTeacherId !== userInfo.teacherId) {
        app.clearWeRunData();
        this.resetPageData();
      }
      
      // 检查缓存的步数数据是否属于当前用户
      const cachedData = app.getWeRunData();
      const isDataForCurrentUser = app.isWeRunDataForUser(userInfo.teacherId);
      
      // 如果缓存数据存在但不属于当前用户，清除它
      if (cachedData && !isDataForCurrentUser) {
        app.clearWeRunData();
        this.resetPageData();
      }
      
      // 保存当前用户的 teacherId
      this.lastTeacherId = userInfo.teacherId;
      
      if (userInfo.avatarUrl) {
        this.setData({
          avatarUrl: userInfo.avatarUrl
        });
      }
      
      // 强制重新获取数据（不使用缓存）
      this.getWeRunData();
    } else {
      // 如果没有用户信息，清除数据并重置页面
      app.clearWeRunData();
      this.resetPageData();
      this.lastTeacherId = null;
    }
  },

  // 重置页面数据
  resetPageData() {
    this.setData({
      todaySteps: 0,
      progressRotation: -180,
      calories: 0,
      totalSteps: 0,
      totalDistance: 0,
      totalCalories: 0,
      monthlyAchievedDays: 0,
      dailySteps: 0,
      dailyDistance: 0,
      recordList: [],
      syncStatus: 'loading'
    });
  },

  // 获取微信运动步数
  getWeRunData() {
    wx.getSetting({
      success: (res) => {
        if (!res.authSetting['scope.werun']) {
          // 先尝试 wx.authorize()，让微信识别该权限
          // 这样在正式版中，设置页面才会显示权限开关
          wx.authorize({
            scope: 'scope.werun',
            success: () => {
              // 授权成功，延迟一下确保授权生效
              setTimeout(() => {
                this.getStepsData();
              }, 500);
            },
            fail: (err) => {
              // 授权失败（通常是用户拒绝过），引导用户去设置页面
              // 此时设置页面会显示权限开关，因为已经触发过权限请求
              if (err.errMsg && err.errMsg.includes('deny')) {
                wx.showModal({
                  title: '提示',
                  content: '需要授权微信运动步数才能使用小程序，请在设置中开启',
                  showCancel: true,
                  confirmText: '去设置',
                  cancelText: '取消',
                  success: (modalRes) => {
                    if (modalRes.confirm) {
                      // 打开设置页面（必须在用户点击事件中调用）
                      wx.openSetting({
                        success: (settingRes) => {
                          if (settingRes.authSetting['scope.werun']) {
                            // 授权成功后延迟一下，确保授权生效
                            setTimeout(() => {
                              this.getStepsData();
                            }, 500);
                          } else {
                            wx.showToast({
                              title: '未开启授权，无法获取步数',
                              icon: 'none',
                              duration: 2000
                            });
                          }
                        },
                        fail: () => {
                          wx.showToast({
                            title: '打开设置失败',
                            icon: 'none',
                            duration: 2000
                          });
                        }
                      });
                    }
                  }
                });
              } else {
                // 其他错误，直接提示
                wx.showModal({
                  title: '提示',
                  content: '需要授权微信运动步数才能使用小程序',
                  showCancel: false
                });
              }
            }
          });
        } else {
          this.getStepsData();
        }
      },
      fail: () => {
        wx.showToast({
          title: '检查授权状态失败',
          icon: 'none',
          duration: 2000
        });
      }
    });
  },

  // 获取步数数据
  getStepsData() {
    wx.getWeRunData({
      success: (res) => {
        // 检查 cloudID 是否存在
        if (!res.cloudID) {
          this.setData({
            syncStatus: 'error'
          });
          wx.showToast({
            title: '获取步数失败：未获取到 cloudID',
            icon: 'none',
            duration: 2000
          });
          return;
        }
        
        // 开始调用云函数时才显示转圈
        this.setData({
          syncStatus: 'loading'
        });
        
        wx.cloud.callFunction({
          name: 'getWeRunData',
          data: {
            weRunData: wx.cloud.CloudID(res.cloudID)
          },
          success: async res => {
            if (res.result && res.result.weRunData) {
              // 重新获取最新的用户信息（防止用户信息在获取数据期间发生变化）
              const userInfo = wx.getStorageSync('userInfo');
              if (!userInfo || !userInfo.teacherId) {
                this.setData({
                  syncStatus: 'error'
                });
                return;
              }
              
              // 再次验证：如果数据获取时的用户和当前用户不一致，不保存
              if (this.lastTeacherId && this.lastTeacherId !== userInfo.teacherId) {
                return;
              }
              
              // 保存到 app 全局数据（同时记录用户ID）
              app.setWeRunData(res.result.weRunData, userInfo.teacherId);

              // 更新显示
              this.updateStepsDisplay(res.result.weRunData);

              // 使用之前获取的 userInfo
              if (userInfo && userInfo.teacherId) {
                // 获取今天的日期
                const today = new Date();
                const dateStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
                
                // 获取30天步数数据
                const stepData = res.result.weRunData.data;
                const stepInfoList = stepData.stepInfoList;

                // 调用stepRecord云函数批量更新步数记录
                try {
                  const result = await wx.cloud.callFunction({
                    name: 'stepRecord',
                    data: {
                      action: 'batchAdd',
                      data: {
                        teacherId: userInfo.teacherId,
                        stepInfoList: stepInfoList
                      }
                    }
                  });

                  if (result.result.code === 0) {
                    // 同步成功
                    this.setData({
                      syncStatus: 'success'
                    });
                  } else {
                    // 同步失败
                    this.setData({
                      syncStatus: 'error'
                    });
                  }
                } catch (err) {
                  // 同步失败
                  this.setData({
                    syncStatus: 'error'
                  });
                }
              }
            } else {
              this.setData({
                syncStatus: 'error'
              });
              wx.showToast({
                title: '获取步数失败：数据格式错误',
                icon: 'none',
                duration: 2000
              });
            }
          },
          fail: err => {
            this.setData({
              syncStatus: 'error'
            });
            wx.showToast({
              title: '获取步数失败：' + (err.errMsg || '网络错误'),
              icon: 'none',
              duration: 2000
            });
          }
        });
      },
      fail: (err) => {
        this.setData({
          syncStatus: 'error'
        });
        wx.showToast({
          title: '获取步数失败：' + (err.errMsg || '授权失败'),
          icon: 'none',
          duration: 2000
        });
      }
    });
  },

  // 更新步数显示
  updateStepsDisplay(weRunData) {
    // 在显示数据前，再次验证当前用户是否匹配
    const userInfo = wx.getStorageSync('userInfo');
    if (!userInfo || !userInfo.teacherId) {
      return;
    }
    
    // 检查数据是否属于当前用户
    const isDataForCurrentUser = app.isWeRunDataForUser(userInfo.teacherId);
    if (!isDataForCurrentUser) {
      return;
    }
    
    const stepData = weRunData.data;
    const stepInfoList = stepData.stepInfoList;
    const todaySteps = stepInfoList[stepInfoList.length - 1].step;
    const totalSteps = stepInfoList.reduce((acc, curr) => acc + curr.step, 0);
    const todayCalories = Math.round(todaySteps * 0.04);
    const totalDistance = (totalSteps * 0.0007).toFixed(2);

    // 处理最近30天的记录（getWeRunData 返回最多30天数据）
    const dailyRecords = stepInfoList
      .map(item => {
        const date = new Date(item.timestamp * 1000);
        const month = date.getMonth() + 1;
        const day = date.getDate();
        const weekDays = ['日', '一', '二', '三', '四', '五', '六'];
        return {
          date: `${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`,
          weekDay: `周${weekDays[date.getDay()]}`,
          steps: item.step,
          distance: (item.step * 0.0007).toFixed(2),
          background: item.step >= 7000 ? 'rgba(250, 157, 59, 0.2)' : '#F5F5F5'
        };
      })
      .reverse();

    // 计算进度条旋转角度
    const progressRotation = todaySteps >= this.data.targetSteps ? 0 : -180 + (todaySteps / this.data.targetSteps) * 180;

    // 计算本月达标天数（步数>=7000的天数）
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1; // 月份从0开始，所以要+1
    
    const monthlyAchievedDays = stepInfoList.filter(item => {
      const date = new Date(item.timestamp * 1000);
      const itemYear = date.getFullYear();
      const itemMonth = date.getMonth() + 1;
      // 筛选出本月的记录，且步数>=7000
      return itemYear === currentYear && itemMonth === currentMonth && item.step >= 7000;
    }).length;

    this.setData({
      todaySteps,
      progressRotation,
      calories: this.formatCalories(todayCalories),
      totalSteps,
      totalDistance,
      totalCalories: this.formatCalories(Math.round(totalSteps * 0.04)),
      monthlyAchievedDays,
      dailySteps: todaySteps,
      dailyDistance: (todaySteps * 0.0007).toFixed(1),
      currentDate: dailyRecords[0] ? dailyRecords[0].date : '',
      weekDay: dailyRecords[0] ? `${dailyRecords[0].date} ${dailyRecords[0].weekDay}` : '',
      recordList: dailyRecords
    });
  },

  // 修改格式化卡路里数值的方法
  formatCalories(calories) {
    if (calories >= 10000) {
      return (calories / 10000).toFixed(1) + '万'; // 例如：12345 显示为 1.2万
    }
    return calories;
  },

  // 重试同步
  retrySync() {
    // 重试时不立即显示转圈，等云函数调用时再显示
    this.getWeRunData();
  }
});