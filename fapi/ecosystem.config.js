module.exports = {
  apps: [{
    name: 'mock-exam-api',
    script: 'venv/bin/uvicorn',
    args: 'app:app --host 0.0.0.0 --port 8000 --workers 4',
    cwd: '/www/wwwroot/mock-exam/fapi',
    interpreter: 'none',
    env: {
      NODE_ENV: 'production',
      LLM_PROVIDER: 'qwen',
      LLM_API_KEY: 'sk-a97a0f733dec44dba628e6873f1b93b3',
      DATABASE_URL: 'mysql+pymysql://mockexam:your_password_here@localhost:3306/mock_exam?charset=utf8mb4',
    },
    error_file: '/www/wwwroot/mock-exam/logs/api-error.log',
    out_file: '/www/wwwroot/mock-exam/logs/api-out.log',
    log_file: '/www/wwwroot/mock-exam/logs/api-combined.log',
    time: true
  }]
}
