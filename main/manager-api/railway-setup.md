# Railway Database Setup Guide

## Step 1: Create Railway MySQL Database

1. Go to [Railway.app](https://railway.app) and create an account
2. Create a new project
3. Click "Add Service" → "Database" → "MySQL"
4. Wait for the database to be provisioned

## Step 2: Get Database Connection Details

In your Railway dashboard, click on your MySQL service and go to the "Variables" tab. You'll find:

- `MYSQL_HOST` (e.g., `containers-us-west-xxx.railway.app`)
- `MYSQL_PORT` (usually `3306`)
- `MYSQL_DATABASE` (usually `railway`)
- `MYSQL_USER` (usually `root`)
- `MYSQL_PASSWORD` (auto-generated)

## Step 3: Configure Your Application

### Option A: Update application-dev.yml directly

Replace the placeholders in `main/manager-api/src/main/resources/application-dev.yml`:

```yaml
url: jdbc:mysql://YOUR_RAILWAY_HOST:YOUR_RAILWAY_PORT/railway?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai&nullCatalogMeansCurrent=true&useSSL=true&allowPublicKeyRetrieval=true
username: YOUR_RAILWAY_USERNAME
password: YOUR_RAILWAY_PASSWORD
```

### Option B: Use Railway profile (Recommended)

1. Update `application.yml` to use the railway profile:
   ```yaml
   spring:
     profiles:
       active: railway
   ```

2. Set environment variables when running your application:
   ```bash
   export RAILWAY_DATABASE_URL="jdbc:mysql://YOUR_HOST:3306/railway?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai&nullCatalogMeansCurrent=true&useSSL=true&allowPublicKeyRetrieval=true"
   export RAILWAY_DATABASE_USERNAME="root"
   export RAILWAY_DATABASE_PASSWORD="your_password"
   ```

### Option C: Use Railway's DATABASE_URL (Most convenient)

Railway provides a `DATABASE_URL` environment variable. You can modify your configuration to use it directly:

```yaml
spring:
  datasource:
    url: ${DATABASE_URL}
```

## Step 4: Initialize Database Schema

The application uses Liquibase to automatically create the database schema when it starts. Make sure your Railway database is accessible and the application will create all necessary tables.

## Step 5: Test Connection

Run your manager-api application and check the logs. You should see successful database connection messages instead of the previous error.

## Troubleshooting

1. **SSL Connection Issues**: Make sure `useSSL=true` and `allowPublicKeyRetrieval=true` are in your connection URL
2. **Timeout Issues**: Railway databases may have connection limits. Consider adding connection timeout parameters
3. **Firewall Issues**: Railway databases are accessible from anywhere by default, so no firewall configuration needed

## Example Railway Connection String

```
jdbc:mysql://containers-us-west-123.railway.app:3306/railway?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai&nullCatalogMeansCurrent=true&useSSL=true&allowPublicKeyRetrieval=true&connectTimeout=30000&socketTimeout=30000
```

Replace `containers-us-west-123.railway.app` with your actual Railway host.
