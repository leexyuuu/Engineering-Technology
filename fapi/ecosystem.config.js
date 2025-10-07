module.exports = {
  apps: [{
    name: 'mock-exam-api',
    script: 'venv/bin/uvicorn',
    args: 'app:app --host 0.0.0.0 --port 8000 --workers 2',
    cwd: '/www/wwwroot/mock-exam/fapi',
    interpreter: 'none',
    env: {
      NODE_ENV: 'production'
    },
    error_file: '/www/wwwroot/mock-exam/logs/api-error.log',
    out_file: '/www/wwwroot/mock-exam/logs/api-out.log',
    log_file: '/www/wwwroot/mock-exam/logs/api-combined.log',
    time: true
  }]
}
