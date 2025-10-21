# GitHub Secrets Setup for Telegram Notifications

## Status
✓ Workflow file updated and pushed to GitHub
✓ Local testing confirmed working (both recipients receive messages)
⚠️ **ACTION REQUIRED**: Add GitHub Secrets

## Why Telegram Didn't Work in Last Run

The GitHub Actions logs showed:
```
Telegram not configured - skipping notification
```

**Cause**: The workflow file references secrets that don't exist yet:
```yaml
echo "TELEGRAM_BOT_TOKEN=${{ secrets.TELEGRAM_BOT_TOKEN }}" >> scraper/.env
echo "TELEGRAM_CHAT_ID=${{ secrets.TELEGRAM_CHAT_ID }}" >> scraper/.env
```

When secrets don't exist, these variables are empty, so the scraper skips Telegram.

## Required GitHub Secrets

You need to add 3 secrets to your GitHub repository:

### 1. DATABASE_URL
```
postgresql://trakio_db_owner:npg_I8pNtnDu3xRQ@ep-empty-sound-a2batz5g-pooler.eu-central-1.aws.neon.tech/trakio_db?sslmode=require&channel_binding=require
```

### 2. TELEGRAM_BOT_TOKEN
```
8202323082:AAGRimO8iScakpFKTHbkwhhbmMbPANX8e3g
```

### 3. TELEGRAM_CHAT_ID
```
6192509415,-4879313859
```
*Note: Comma-separated values send to both personal chat and BoB group*

## How to Add Secrets

1. Go to your repository on GitHub:
   ```
   https://github.com/Ismat-Samadov/lead_generator
   ```

2. Navigate to: **Settings** → **Secrets and variables** → **Actions**

3. Click **"New repository secret"** for each of the 3 secrets above

4. Enter the **Name** (e.g., `TELEGRAM_BOT_TOKEN`) and **Value** exactly as shown above

5. Click **"Add secret"**

## Testing After Setup

Once secrets are added:

1. Go to **Actions** tab in GitHub
2. Select **"Daily Lead Scraper"** workflow
3. Click **"Run workflow"** → **"Run workflow"** (manual trigger)
4. Wait for completion (~2-3 minutes)
5. Check Telegram for notification in both:
   - Your personal chat
   - BoB group

## Expected Telegram Message Format

```
✅ Multi-Source Scraping Report

📊 Overall Statistics
━━━━━━━━━━━━━━━━━━
📋 Total Listings: 750
📱 Phones Extracted: 650 (86.7%)
💾 New Saved: 45 (6.9%)
🔄 Duplicates/Invalid: 605
❌ Failed: 100

📍 By Source
━━━━━━━━━━━━━━━━━━
✅ EVV.AZ: 475/550 (86.4%) | Saved: 30
✅ Villa.AZ: 175/200 (87.5%) | Saved: 15

⏱ Performance
━━━━━━━━━━━━━━━━━━
⏳ Total Duration: 125.50s
⚡ Overall Speed: 6.0 listings/sec

🎯 Status: Excellent
```

## Automated Schedule

After secrets are added, the scraper will run automatically:
- **Daily at 13:00 UTC** (4:00 PM Azerbaijan Time)
- Sends Telegram notifications after each run
- No manual intervention needed

## Local Testing Already Confirmed Working

```
✓ Sent to chat 6192509415
✓ Sent to chat -4879313859
Telegram: 2/2 messages sent successfully
✓ Test notification sent successfully!
```

## Summary

**What's Done:**
- ✓ Phone validation system
- ✓ Telegram notification system
- ✓ Multi-recipient support (personal + BoB group)
- ✓ Villa.AZ phone extraction fixed (82.5% success rate)
- ✓ Workflow file updated and pushed

**What You Need to Do:**
1. Add 3 GitHub secrets (5 minutes)
2. Test manual workflow run
3. Enjoy automated daily reports!
