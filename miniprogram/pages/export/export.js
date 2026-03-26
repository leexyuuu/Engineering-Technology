Page({
  data: {
    selectedYear: new Date().getFullYear(),
    selectedMonth: new Date().getMonth() + 1,
    years: [],
    months: [
      { value: 1, label: '1月' },
      { value: 2, label: '2月' },
      { value: 3, label: '3月' },
      { value: 4, label: '4月' },
      { value: 5, label: '5月' },
      { value: 6, label: '6月' },
      { value: 7, label: '7月' },
      { value: 8, label: '8月' },
      { value: 9, label: '9月' },
      { value: 10, label: '10月' },
      { value: 11, label: '11月' },
      { value: 12, label: '12月' }
    ],
    isExporting: false
  },

  onLoad() {
    // 检查用户权限
    const userInfo = wx.getStorageSync('userInfo');
    if (!userInfo || userInfo.role !== 1) {
      wx.showToast({
        title: '权限不足',
        icon: 'error'
      });
      setTimeout(() => {
        wx.navigateBack();
      }, 1500);
      return;
    }

    // 生成年份选项（最近5年）
    const currentYear = new Date().getFullYear();
    const years = [];
    for (let i = currentYear; i >= currentYear - 4; i--) {
      years.push({ value: i, label: `${i}年` });
    }
    this.setData({ 
      years,
      selectedYearIndex: 0,
      selectedMonthIndex: this.data.selectedMonth - 1
    });
  },

  onYearChange(e) {
    const index = parseInt(e.detail.value);
    this.setData({
      selectedYear: this.data.years[index].value,
      selectedYearIndex: index
    });
  },

  onMonthChange(e) {
    const index = parseInt(e.detail.value);
    this.setData({
      selectedMonth: this.data.months[index].value,
      selectedMonthIndex: index
    });
  },

  async onExport() {
    if (this.data.isExporting) return;

    const { selectedYear, selectedMonth } = this.data;
    
    // 验证选择的日期不能是未来月份
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1;
    
    if (selectedYear > currentYear || (selectedYear === currentYear && selectedMonth > currentMonth)) {
      wx.showToast({
        title: '不能导出未来月份',
        icon: 'error'
      });
      return;
    }

    this.setData({ isExporting: true });
    wx.showLoading({
      title: '导出中...',
      mask: true
    });

    try {
      const res = await wx.cloud.callFunction({
        name: 'exportStepStatistics',
        data: { 
          year: selectedYear, 
          month: selectedMonth,
          source: 'admin' // 标记为管理员调用
        }
      });

      if (res.result && res.result.code === 0) {
        // 复制下载链接到剪贴板
        wx.setClipboardData({
          data: res.result.data.downloadUrl,
          success: () => {
            wx.showModal({
              title: '导出成功',
              content: `已成功导出${selectedYear}年${selectedMonth}月的数据。\n总人数：${res.result.data.totalCount}人\n达标人数：${res.result.data.qualifiedCount}人\n\n下载链接已复制到剪贴板，请粘贴到浏览器中下载。`,
              showCancel: false,
              success: () => {
                wx.navigateBack();
              }
            });
          }
        });
      } else {
        wx.showToast({
          title: res.result ? res.result.message : '导出失败',
          icon: 'error'
        });
      }
    } catch (error) {
      console.error('导出失败：', error);
      wx.showToast({
        title: '导出异常',
        icon: 'error'
      });
    } finally {
      this.setData({ isExporting: false });
      wx.hideLoading();
    }
  }
});
