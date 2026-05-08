# Render Deployment Guide

## Prerequisites
- Render account
- GitHub repository with your Django project

## Deployment Steps

### 1. Connect to Render
1. Go to [render.com](https://render.com) and sign in
2. Click "New +" and select "Blueprint" (or "Web Service" if you prefer manual setup)

### 2. Connect Repository
- Connect your GitHub repository
- Render will detect the `render.yaml` file and auto-configure PostgreSQL

### 3. Environment Variables
The following environment variables are automatically set by `render.yaml`:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Auto-generated secret key
- `DEBUG`: Set to `false`

### 4. Deploy
- Click "Create Web Service"
- Render will build and deploy your app
- The release command will run migrations and create demo users

## Demo Users
After deployment, you can log in with:
- **Admin**: `admin1` / `password`
- **User**: `user1` / `password`
- **Guard**: `guard1` / `password`

## Troubleshooting

### 500 Error After Login
- Check that migrations ran successfully in the release phase
- Verify demo users were created
- Check Render logs for database connection issues

### Static Files Not Loading
- Ensure `STATIC_ROOT` is set and WhiteNoise is configured
- Check that `python manage.py collectstatic` runs during build

### Database Issues
- Confirm `DATABASE_URL` environment variable is set
- Check PostgreSQL database is properly provisioned

## Manual Setup (if not using render.yaml)
If you prefer manual setup:
1. Create a PostgreSQL database in Render
2. Set the `DATABASE_URL` environment variable
3. Set `SECRET_KEY` and `DEBUG=false`
4. Use the Procfile for web/release commands