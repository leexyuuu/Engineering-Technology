#!/bin/bash

# 部署定时触发器脚本
echo "开始部署定时触发器..."

# 进入云函数目录
cd cloudfunctions/exportStepStatistics

# 上传云函数
echo "上传云函数..."
wx-server-sdk deploy

# 上传触发器配置
echo "上传触发器配置..."
wx-server-sdk deploy --config config.json

echo "部署完成！"
echo "定时触发器将在每月1号凌晨2点自动执行"
echo "生成上个月的步数达标老师名单"
