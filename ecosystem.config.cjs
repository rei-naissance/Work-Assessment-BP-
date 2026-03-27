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
      script: '.venv/bin/uvicorn',
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
      // Serve pre-built SPA with `serve` (npm i -g serve)
      // For Docker deployments, Nginx-based Dockerfile is preferred.
      name: 'frontend',
      cwd: './frontend',
      script: 'npx',
      args: `serve dist -s -l ${FRONTEND_PORT}`,
      interpreter: 'none',
      env: {
        NODE_ENV: 'development',
      },
      env_production: {
        NODE_ENV: 'production',
      },
    },
  ],
};
