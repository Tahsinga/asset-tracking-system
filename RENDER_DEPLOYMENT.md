# Deploying to Render

## Key Changes Made for Production

1. **PostgreSQL Database** - Changed from SQLite to PostgreSQL (SQLite doesn't persist on Render)
2. **Static Files** - Configured WhiteNoise for serving static files
3. **Environment Variables** - Updated settings to use environment variables for sensitive data
4. **Management Command** - Created Django management command to create demo users

## Deployment Steps

### 1. Push Code to GitHub
```bash
git add .
git commit -m "Configure for Render deployment"
git push
```

### 2. Create Render Service
1. Go to [render.com](https://render.com)
2. Click "New +" and select "Web Service"
3. Select your GitHub repository
4. Choose deployment method:
   - **Option A (Recommended)**: Use `render.yaml` file (automatic PostgreSQL setup)
   - **Option B**: Manual setup with Procfile

### 3. Set Environment Variables
If not using render.yaml, manually add these in Render dashboard:
- `SECRET_KEY`: Generate a strong random key
- `DEBUG`: Set to `False`
- `DATABASE_URL`: Render will create this automatically if using PostgreSQL

### 4. Create Demo Users in Production
After first deployment, run this command via Render Shell:
```bash
python manage.py migrate
python manage.py create_demo_users
```

Or use Render's "Connect" shell and paste the commands above.

## Demo User Credentials

After running `create_demo_users`, these accounts will be available:

| Username | Password | Role |
|----------|----------|------|
| user1    | password | User |
| admin1   | password | Admin |
| guard1   | password | Gate Guard |

## Important Notes

- **Never commit your database file** - It's in .gitignore for good reason
- **Always use PostgreSQL on Render** - SQLite files get deleted on deploy/restart
- **Keep SECRET_KEY secret** - Generate a new one for production
- **Run migrations** - The Procfile automatically runs migrations on deployment

## Troubleshooting

### 500 Error After Login
This usually means the database migration didn't run. Check Render logs and manually run:
```
python manage.py migrate
python manage.py create_demo_users
```

### Static Files Not Loading
Make sure `collect static` runs. Check that WhiteNoise middleware is in MIDDLEWARE list in settings.py.

### Database Connection Issues
Verify `DATABASE_URL` environment variable is set correctly in Render dashboard.
