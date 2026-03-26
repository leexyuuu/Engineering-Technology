Page({
    data: {
        code: '',
        isAgreePolicy: false
    },

    onLoad() {
        // 页面加载时先获取微信登录凭证
        wx.login({
            success: (res) => {
                if (res.code) {
                    this.setData({
                        code: res.code
                    });
                }
            }
        });
    },

    handlePrivacyChange(e) {
        this.setData({
            isAgreePolicy: e.detail.value.length > 0
        });
    },

    // 跳转到用户协议页面
    navigateToAgreement() {
        wx.navigateTo({
            url: '/pages/agreement/agreement'
        });
    },

    // 跳转到隐私政策页面
    navigateToPrivacy() {
        wx.navigateTo({
            url: '/pages/privacy/privacy'
        });
    },

    handleSubmit(e) {
        const {
            name,
            employeeId
        } = e.detail.value;

        // 检查是否同意隐私政策
        if (!this.data.isAgreePolicy) {
            wx.showToast({
                title: '请先同意隐私政策',
                icon: 'none'
            });
            return;
        }

        // 验证表单数据
        if (!name) {
            wx.showToast({
                title: '请填写姓名',
                icon: 'none'
            });
            return;
        }
        
        if (!employeeId) {
            wx.showToast({
                title: '请填写工号',
                icon: 'none'
            });
            return;
        }

        wx.showLoading({
            title: '登录中...',
            mask: true
        });

        // 调用云函数
        wx.cloud.callFunction({
            name: 'login',
            data: {
                name: name,
                employeeId: employeeId,
                code: this.data.code
            },
            success: (res) => {
                wx.hideLoading();

                if (res.result && res.result.code === 0) {
                    // 获取 app 实例并清除所有旧数据
                    const app = getApp();
                    app.clearWeRunData();
                    
                    // 清除所有本地存储的缓存数据（如果有的话）
                    try {
                        wx.removeStorageSync('weRunData');
                        wx.removeStorageSync('cachedSteps');
                    } catch(e) {
                        // 忽略清除缓存的错误
                    }
                    
                    // 登录成功，保存新的用户信息
                    const newUserInfo = {
                        openid: res.result.openid,
                        name: res.result.name,
                        teacherId: res.result.teacherId,
                        avatarUrl: res.result.avatarUrl || '/images/default-avatar.png',
                        department: res.result.department || '', // 保存部门信息
                        role: res.result.role || 0
                    };
                    wx.setStorageSync('userInfo', newUserInfo);

                    wx.showToast({
                        title: '登录成功',
                        icon: 'success'
                    });

                    setTimeout(() => {
                        // 使用 reLaunch 确保页面完全重新加载
                        wx.reLaunch({
                            url: '/pages/index/index'
                        });
                    }, 1000);
                } else {
                    // 登录失败，显示服务端返回的错误信息
                    wx.showModal({
                        title: '提示',
                        content: res.result ? res.result.message : '登录失败，请重试',
                        showCancel: false
                    });
                }
            },
            fail: (err) => {
                console.error("云函数调用失败：", err);
                wx.hideLoading();
                wx.showModal({
                    title: '提示',
                    content: '登录失败，请重试',
                    showCancel: false
                });
            }
        });
    }
});