const BACKEND_PORT = process.env.BACKEND_PORT || '7691';
const FRONTEND_PORT = process.env.FRONTEND_PORT || '7680';
const MONGO_URI = process.env.MONGO_URI || process.env.MONGODB_URI || 'mongodb://localhost:27017/home_binder';
const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379';
const JWT_SECRET = process.env.JWT_SECRET || 'change-me-in-production';
const DATA_DIR = process.env.DATA_DIR || './data/binders';
const RESEND_API_KEY = process.env.RESEND_API_KEY || '';
const FROM_EMAIL = process.env.FROM_EMAIL || 'noreply@mybinderpro.com';
const WEB_CONCURRENCY = process.env.WEB_CONCURRENCY || '2';

module.exports = {
  apps: [
    {
      name: 'backend',
      cwd: './backend',
      script: 'venv/bin/uvicorn',
      args: `app.main:app --host 0.0.0.0 --port ${BACKEND_PORT} --workers ${WEB_CONCURRENCY} --proxy-headers --forwarded-allow-ips=*`,
      interpreter: 'none',
      env: {
        MONGO_URI,
        REDIS_URL,
        JWT_SECRET,
        DATA_DIR,
        PORT: BACKEND_PORT,
        RESEND_API_KEY,
        FROM_EMAIL,
        ENVIRONMENT: 'development',
        NODE_ENV: 'development',
      },
      env_production: {
        MONGO_URI,
        REDIS_URL,
        JWT_SECRET,
        DATA_DIR,
        PORT: BACKEND_PORT,
        RESEND_API_KEY,
        FROM_EMAIL,
        ENVIRONMENT: 'production',
        NODE_ENV: 'production',
      },
    },
    {
      // ARQ background worker for PDF generation
      name: 'worker',
      cwd: './backend',
      script: '.venv/bin/arq',
      args: 'app.worker.WorkerSettings',
      interpreter: 'none',
      env: {
        MONGO_URI,
        REDIS_URL,
        JWT_SECRET,
        DATA_DIR,
        RESEND_API_KEY,
        FROM_EMAIL,
        ENVIRONMENT: 'development',
      },
      env_production: {
        MONGO_URI,
        REDIS_URL,
        JWT_SECRET,
        DATA_DIR,
        RESEND_API_KEY,
        FROM_EMAIL,
        ENVIRONMENT: 'production',
      },
    },
    {
      // Serve pre-built SPA with `vite preview`.
      //
      // NOTE: `vite preview` is for LOCAL development only. It is not production-grade.
      // For production, replace this process with nginx:
      //
      //   1. sudo apt install nginx
      //   2. Copy frontend/nginx.conf to /etc/nginx/sites-available/binderpro
      //   3. Change `proxy_pass http://backend:7691` to `proxy_pass http://localhost:7691`
      //   4. Change `root /usr/share/nginx/html` to the absolute path of frontend/dist
      //   5. sudo ln -s /etc/nginx/sites-available/binderpro /etc/nginx/sites-enabled/
      //   6. sudo rm /etc/nginx/sites-enabled/default
      //   7. sudo nginx -t && sudo systemctl enable nginx && sudo systemctl start nginx
      //   8. pm2 delete frontend  (nginx replaces this process)
      //
      // See docs/ARCHITECTURE.md → Deployment for full instructions.
      name: 'frontend',
      cwd: './frontend',
      script: 'npx',
      args: `vite preview`,
      interpreter: 'none',
      env: {
        NODE_ENV: 'development',
        PORT: FRONTEND_PORT,
        VITE_API_PORT: '7691',
      },
      env_production: {
        NODE_ENV: 'production',
        PORT: FRONTEND_PORT,
        VITE_API_PORT: '7691',
      },
    },
  ],
};
