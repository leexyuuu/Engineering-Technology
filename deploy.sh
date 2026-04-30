#!/bin/bash
# ============================================================
# Mock-Exam 考试系统 - 阿里云宝塔服务器完整部署脚本
# 包含：学生前端 / 管理后台 / FastAPI 后端
# ============================================================

set -e

# ---- 配置区域（根据实际情况修改） ----
PROJECT_DIR="/www/wwwroot/mock-exam"
STUDENT_DEPLOY_DIR="/www/wwwroot/mock-exam"
ADMIN_DEPLOY_DIR="/www/wwwroot/mock-exam/admin"
GIT_BRANCH="master"
PYTHON_VENV="${PROJECT_DIR}/fapi/venv"
LOG_DIR="${PROJECT_DIR}/logs"

# ---- 颜色输出 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ---- 拉取最新代码 ----
pull_code() {
    log_info "拉取最新代码..."
    cd "$PROJECT_DIR"
    git pull origin "$GIT_BRANCH"
    log_info "代码更新完成"
}

# ---- 构建学生前端 ----
build_student_frontend() {
    log_info "========== 构建学生前端 =========="
    cd "${PROJECT_DIR}/frontend/ai-exam"

    rm -rf dist/
    rm -rf node_modules/.vite/

    log_info "安装依赖..."
    npm install

    log_info "构建生产版本..."
    npm run build

    log_info "部署到 ${STUDENT_DEPLOY_DIR} ..."
    \cp -rf dist/* "$STUDENT_DEPLOY_DIR/"

    log_info "学生前端构建部署完成"
}

# ---- 构建管理后台 ----
build_admin() {
    log_info "========== 构建管理后台 =========="
    cd "${PROJECT_DIR}/admin"

    rm -rf dist/

    log_info "安装依赖..."
    npm install

    log_info "构建生产版本（publicPath=/admin/）..."
    VUE_APP_PUBLIC_PATH=/admin/ npm run build:prod

    log_info "部署到 ${ADMIN_DEPLOY_DIR} ..."
    mkdir -p "$ADMIN_DEPLOY_DIR"
    \cp -rf dist/* "$ADMIN_DEPLOY_DIR/"

    log_info "管理后台构建部署完成"
}

# ---- 部署后端 ----
deploy_backend() {
    log_info "========== 部署后端 =========="
    cd "${PROJECT_DIR}/fapi"

    # 创建虚拟环境（如不存在）
    if [ ! -d "$PYTHON_VENV" ]; then
        log_info "创建 Python 虚拟环境..."
        python3 -m venv "$PYTHON_VENV"
    fi

    log_info "安装 Python 依赖..."
    source "${PYTHON_VENV}/bin/activate"
    pip install -r requirements.txt -q
    deactivate

    # 创建日志目录
    mkdir -p "$LOG_DIR"

    # 加载环境变量（LLM_API_KEY等）
    [ -f /etc/environment ] && source /etc/environment

    # 重启后端服务
    log_info "重启后端服务..."
    if pm2 describe mock-exam-api > /dev/null 2>&1; then
        pm2 restart mock-exam-api
    else
        pm2 start ecosystem.config.js
    fi

    pm2 save

    log_info "后端部署完成"
}

# ---- 部署状态检查 ----
check_status() {
    log_info "========== 部署状态检查 =========="

    echo ""
    log_info "PM2 服务状态:"
    pm2 list

    echo ""
    log_info "后端健康检查:"
    sleep 2
    if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ | grep -q "200"; then
        log_info "后端 API 运行正常 (port 8000)"
    else
        log_warn "后端 API 可能未就绪，请检查日志: ${LOG_DIR}/api-error.log"
    fi

    echo ""
    log_info "Nginx 状态:"
    systemctl status nginx --no-pager -l | head -5

    echo ""
    log_info "部署完成！"
    echo "  学生端: http://你的域名/"
    echo "  管理端: http://你的域名/admin/"
    echo "  后端API: http://127.0.0.1:8000/"
}

# ---- 生成 Nginx 配置示例 ----
generate_nginx_config() {
    cat << 'NGINX_EOF'
# ============================================================
# Nginx 配置示例 - 放到宝塔网站设置的配置文件中
# ============================================================

server {
    listen 80;
    server_name your-domain.com;  # 改成你的域名
    root /www/wwwroot/mock-exam;
    index index.html;

    # 学生前端 (根路径)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 管理后台 (/admin/)
    location /admin/ {
        alias /www/wwwroot/mock-exam/admin/;
        try_files $uri $uri/ /admin/index.html;
    }

    # API 代理到 FastAPI 后端
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 100m;
    }

    # 上传文件访问
    location /uploads/ {
        proxy_pass http://127.0.0.1:8000/uploads/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    access_log /www/wwwlogs/mock-exam.log;
    error_log /www/wwwlogs/mock-exam.error.log;
}
NGINX_EOF
}

# ---- 主流程 ----
main() {
    echo "============================================================"
    echo "  Mock-Exam 考试系统部署脚本"
    echo "============================================================"
    echo ""

    case "${1:-all}" in
        all)
            pull_code
            build_student_frontend
            build_admin
            deploy_backend
            check_status
            ;;
        student)
            pull_code
            build_student_frontend
            log_info "学生前端部署完成"
            ;;
        admin)
            pull_code
            build_admin
            log_info "管理后台部署完成"
            ;;
        backend)
            pull_code
            deploy_backend
            log_info "后端部署完成"
            ;;
        frontend)
            pull_code
            build_student_frontend
            build_admin
            log_info "前端(学生+管理)部署完成"
            ;;
        nginx-config)
            generate_nginx_config
            ;;
        status)
            check_status
            ;;
        *)
            echo "用法: $0 {all|student|admin|backend|frontend|nginx-config|status}"
            echo ""
            echo "  all          - 完整部署（默认）"
            echo "  student      - 只部署学生前端"
            echo "  admin        - 只部署管理后台"
            echo "  backend      - 只部署后端"
            echo "  frontend     - 部署学生前端 + 管理后台"
            echo "  nginx-config - 输出 Nginx 配置示例"
            echo "  status       - 查看部署状态"
            exit 1
            ;;
    esac
}

main "$@"
