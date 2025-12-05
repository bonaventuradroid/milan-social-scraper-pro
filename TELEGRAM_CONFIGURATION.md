# 📱 TELEGRAM CONFIGURATION GUIDE

## Quick Setup (5 minutes)

The Milan Rentals n8n workflow is now configured to send Telegram notifications. However, you need to set your **Telegram Chat ID** to activate alerts.

### Step 1: Find Your Telegram Chat ID

#### Option A: Using a Bot (Recommended)

1. Open Telegram and search for **@userinfobot**
2. Click "Start" or send `/start`
3. The bot will show your User ID (e.g., `123456789`)
4. Copy this ID

#### Option B: Group Chat ID

1. Create or use an existing Telegram group
2. Add **@userinfobot** to the group
3. Send `/start` in the group
4. The bot will show the Chat ID (format: `-100123456789` for groups)
5. Copy this ID

### Step 2: Update n8n Workflow

1. Go to your n8n workflow: **Milan Rentals ENTERPRISE 99%**
2. Find the **Telegram** node (the blue paper plane icon 📨)
3. Double-click to open the configuration
4. Look for the **Chat ID** field
5. Replace the placeholder `-1001234567890` with your real Telegram ID
6. Click the checkmark ✅ to save
7. Click **Save** (top right button)

### Step 3: Test the Connection

1. In the Telegram node, click **"Execute step"** button
2. If successful:
   - ✅ Green checkmark appears
   - You'll receive a test message on Telegram
   - The error banner disappears
3. If it fails:
   - ❌ Red error icon shows
   - Check that the Chat ID is correct
   - Ensure Telegram credentials in n8n are valid

---

## 🔧 Configuration Reference

### Telegram Node Settings

| Setting | Value | Description |
|---------|-------|-------------|
| **Resource** | Message | Select "Message" to send text |
| **Operation** | Send Message | Select "Send Message" operation |
| **Credential** | Telegram account | Your Telegram Bot account |
| **Chat ID** | Your ID here | Replace `-1001234567890` with your real ID |
| **Text** | Dynamic (from Format node) | Message text from previous node |

### Telegram Chat ID Formats

- **Personal Chat**: `123456789` (9-10 digits)
- **Group Chat**: `-100123456789` (starts with -100)
- **Channel**: `-100987654321` (starts with -100)

### Finding Your ID (Alternative Methods)

**Method 1: Via Message Forward**
1. Forward any message from your chat to **@getidsbot**
2. The bot replies with your Chat ID

**Method 2: Via Telegram API**
1. In Telegram Web: Open DevTools (F12)
2. Look for chat IDs in network requests

---

## ✅ Verification Checklist

- [ ] Telegram Chat ID obtained
- [ ] Chat ID updated in n8n workflow
- [ ] Telegram node shows no error (no red icon)
- [ ] Test message received successfully
- [ ] Workflow saved ("Saved" status visible)

---

## 🆘 Troubleshooting

### Error: "chat not found"
**Solution**: The Chat ID is invalid or doesn't exist
- Double-check the Chat ID format (no spaces, correct number)
- Make sure you're using YOUR Chat ID, not someone else's
- For groups, ensure the format starts with `-100`

### Error: "unauthorized"
**Solution**: Telegram credentials are incorrect
- Verify the Telegram bot token in n8n Credentials
- Regenerate the token from @BotFather if needed
- Re-add the credentials to n8n

### No error but no message received
**Solution**: The workflow might not be sending data
- Check that "Has Results?" node is returning true
- Verify workflow is "Active" (toggle switch enabled)
- Execute a test run manually

### Test message appears but scheduled messages don't
**Solution**: GitHub Actions might not be running
- Check GitHub Actions workflow status
- Verify the schedule time in `.github/workflows/facebook-scraper.yml`
- Confirm the workflow file was committed properly

---

## 📖 Related Documentation

- Main README: `README.md`
- Fixes Summary: `FIXES_SUMMARY.md`
- Test Report: `TEST_REPORT_SEVERE.md`
- GitHub Actions: `.github/workflows/facebook-scraper.yml`

---

## 🔒 Security Notes

⚠️ **Important**: 
- Never share your Chat ID publicly
- Don't commit Chat IDs to version control
- Use environment variables in production (Enterprise plan required)
- Keep your Telegram bot token secret

---

## ✨ What Happens Next

Once configured, your workflow will:

1. **Run every 6 hours** (via GitHub Actions scheduler)
2. **Scrape data** from Facebook Groups and Nextdoor
3. **Process listings** (deduplication, AI scoring)
4. **Send Telegram notification** with new listings summary
5. **Update Google Sheets** with all data

Example notification:
```
🎯 🔴 NUOVI ANNUNCI MILANO 🔴 🎯

✅ **1 annunci rilevati**

📊 PREMIUM:
• Totale: 1 annunci
• Ranges: €200-€200
• Piattaforme: 1 Unknown
```

---

*Last updated: 2024*
*Status: Active & Production Ready ✅*
