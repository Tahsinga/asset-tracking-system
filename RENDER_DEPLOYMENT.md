# Render Deployment Guide

## ✅ Fixed Issues

The app now supports **PostgreSQL for production** while keeping SQLite for local development.

- ✅ SQLite works locally (no changes needed)
- ✅ PostgreSQL auto-configured on Render via `render.yaml`
- ✅ Demo users auto-created on release
- ✅ Static files handled by WhiteNoise
- ✅ Security settings for production

## 📦 Requirements Changes

Added to `requirements.txt`:
- `psycopg2-binary==2.9.9` - PostgreSQL database adapter
- `dj-database-url==2.1.0` - Parse DATABASE_URL environment variable

## 🚀 Deploy to Render

### Option 1: Auto-Deploy with render.yaml (Easiest)

1. Push changes to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click "New" → "Blueprint"
4. Connect your GitHub repo
5. Select branch → Create

Render will:
- Create PostgreSQL database automatically
- Run migrations
- Create demo users (user1, admin1, guard1)
- Deploy with gunicorn

### Option 2: Manual Deploy

1. Create new **Web Service** on Render
2. Connect GitHub repo
3. Set environment variables:
   ```
   DEBUG=False
   ALLOWED_HOSTS=your-app.onrender.com
   SECRET_KEY=[generate a strong key]
   ```
4. Set **Database** to PostgreSQL (free tier)
5. Set **Start Command**:
   ```
   gunicorn webapp.wsgi:application
   ```
6. Set **Build Command**:
   ```
   pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py create_demo_users
   ```

## 🔐 Demo Users (Production)

After deployment, login with:
- **User1** (Regular User)
  - Username: `user1`
  - Password: `password`
  - Role: `User`

- **Admin1** (Admin)
  - Username: `admin1`
  - Password: `password`
  - Role: `Admin`

- **Guard1** (Gate Guard)
  - Username: `guard1`
  - Password: `password`
  - Role: `Gate Guard`

## 🧪 Test Locally

```bash
# Create demo data
python manage.py create_demo_users

# Run development server
python manage.py runserver

# Visit http://127.0.0.1:8000/login/
```

## ⚠️ Production Checklist

- [x] DEBUG = False in production
- [x] SECRET_KEY from environment variable
- [x] ALLOWED_HOSTS configured correctly
- [x] CSRF_TRUSTED_ORIGINS for your domain
- [x] Static files collected (WhiteNoise handles serving)
- [x] Database migrations run on release
- [x] Demo users created on release
- [x] Logs visible in Render dashboard

## 🐛 Troubleshooting

### Still getting 500 error?

Check Render logs:
1. Go to your service on Render
2. Click "Logs" tab
3. Look for error messages

Common issues:
- **Database migration failed**: Check that Render PostgreSQL is connected
- **Import errors**: Make sure all packages are in `requirements.txt`
- **Static files 404**: WhiteNoise needs to be in MIDDLEWARE

### Users not creating?

Run manually in Render shell:
```bash
python manage.py create_demo_users
```
