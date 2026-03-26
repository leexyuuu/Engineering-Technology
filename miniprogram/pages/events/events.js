Page({
  data: {
    events: [
      {
        title: '杉达健康习惯养成赛',
        desc: '新增每天6000步达标赛！',
        participants: 856,
        image: '/images/event-habit.png',
        backgroundColor: '#E6F3FB'
      },
      {
        title: '春天健走闯关赛',
        desc: '每3天一期，等你来玩！',
        participants: 234,
        image: '/images/event-challenge.png',
        backgroundColor: '#E8F6F1'
      },
      {
        title: '邀你来战天天赏金赛',
        desc: '小组达标领红包奖励！',
        participants: 678,
        image: '/images/event-reward.png',
        backgroundColor: '#FFF0F0',
        isHot: true
      },
      {
        title: '杉达跨年迎新赛',
        desc: '新增每天6000步达标赛！',
        participants: 856,
        image: '/images/event-habit.png',
        backgroundColor: '#F7F8FA'
      },
      {
        title: '健走闯关赛',
        desc: '每3天一期，等你来玩！',
        participants: 234,
        image: '/images/event-challenge.png',
        backgroundColor: '#E8F6F1'
      },
      {
        title: '天天赏金赛',
        desc: '小组达标领红包奖励！',
        participants: 678,
        image: '/images/event-reward.png',
        backgroundColor: '#FFF0F0',
        isHot: true
      }
    ]
  },

  onLoad() {
    this.createContext();
    this.loadImages();
  },

  createContext() {
    const query = wx.createSelectorQuery();
    query.select('#myCanvas')
      .fields({ node: true, size: true })
      .exec((res) => {
        const canvas = res[0].node;
        this.ctx = canvas.getContext('2d');
        
        // 设置canvas大小
        canvas.width = 100;
        canvas.height = 100;
      });
  },

  loadImages() {
    this.data.events.forEach((event, index) => {
      this.getImageColor(event.image, index);
    });
  },

  getImageColor(imagePath, index) {
    const img = wx.createImage();
    img.src = imagePath;
    
    img.onload = () => {
      // 绘制图片
      this.ctx.drawImage(img, 0, 0, 100, 100);
      
      // 获取图片数据
      const imageData = this.ctx.getImageData(0, 0, 100, 100);
      const data = imageData.data;
      
      // 计算平均颜色
      let r = 0, g = 0, b = 0;
      const total = data.length / 4;
      
      for (let i = 0; i < data.length; i += 4) {
        r += data[i];
        g += data[i + 1];
        b += data[i + 2];
      }
      
      r = Math.round(r / total);
      g = Math.round(g / total);
      b = Math.round(b / total);
      
      // 创建浅色背景
      const backgroundColor = `rgba(${r}, ${g}, ${b}, 0.1)`;
      
      // 更新状态
      this.setData({
        [`events[${index}].backgroundColor`]: backgroundColor
      });
    };
  }
}); 