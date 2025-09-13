# Render Sync Setup Guide

## 🚫 **Daily Syncer Limitation on Render**

**Render does NOT support cron jobs or background processes** on web services. However, here are several solutions:

## ✅ **Solution 1: GitHub Actions (Recommended)**

We've set up GitHub Actions to run daily sync automatically:

1. **Go to your GitHub repository**
2. **Navigate to Actions tab**
3. **Enable the "Daily Stock Data Sync" workflow**
4. **Add your DATABASE_URL as a secret:**
   - Go to Settings → Secrets and variables → Actions
   - Add new secret: `DATABASE_URL` with your PostgreSQL connection string

**Schedule:** Runs daily at 6:00 PM IST (12:30 PM UTC)

## ✅ **Solution 2: External Cron Service**

Use external services like:
- **Cron-job.org** (Free)
- **EasyCron** (Paid)
- **SetCronJob** (Free tier available)

**Setup:**
1. Create account on any cron service
2. Add job with URL: `https://your-render-app.onrender.com/api/trigger-daily-sync`
3. Set method: POST
4. Schedule: Daily at your preferred time

## ✅ **Solution 3: Manual Admin Panel**

Access the admin panel at: `https://your-render-app.onrender.com/admin`

**Features:**
- ✅ **Manual sync trigger**
- ✅ **Test sync** (single stock)
- ✅ **Real-time status** monitoring
- ✅ **Error logging**

## ✅ **Solution 4: Render Cron Service (Paid)**

If you upgrade to Render Pro:
1. **Create a Cron Service**
2. **Set build command:** `pip install -r requirements.txt`
3. **Set start command:** `python scripts/daily_ohlcv_syncer.py`
4. **Schedule:** Daily

## 🔧 **Current Setup**

Your app now includes:
- ✅ **API endpoints** for sync management
- ✅ **Admin panel** for manual control
- ✅ **GitHub Actions** workflow
- ✅ **Background task** support

## 📊 **Monitoring**

Check sync status at:
- **Admin Panel:** `/admin`
- **API Status:** `/api/sync-status`
- **Trigger Sync:** `/api/trigger-daily-sync` (POST)

## 🚀 **Deployment**

All changes are ready for Render deployment. The app will work perfectly with any of the above sync solutions!
