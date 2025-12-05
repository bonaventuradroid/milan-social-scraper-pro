# 🚀 Milan Social Scraper Pro

> **Smart FB Groups & Nextdoor Scraper** con integrazione n8n, anti-ban avanzato, GitHub Actions scheduler e Cloudflare Workers proxy.

[![GitHub](https://img.shields.io/badge/github-milan--social--scraper--pro-blue?logo=github)](https://github.com/bonaventuradroid/milan-social-scraper-pro)
[![License](https://img.shields.io/badge/license-MIT-green)](#license)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](#requirements)

## 📋 Panoramica

Sistema automatizzato per scraping intelligente di annunci immobiliari da Facebook Groups e Nextdoor con protezioni anti-ban, integrazione n8n webhook, notifiche Telegram e scheduling 24/7 via GitHub Actions.

### ✨ Caratteristiche

- **🤖 Playwright Automation**: Browser automation headless con stealth plugin
- **🔐 Anti-Ban Multi-Layer**: Cookie persistence, User-Agent rotation, random delays umani
- **⚡ GitHub Actions Scheduler**: 3 esecuzioni/giorno (6AM, 2PM, 10PM CET)
- **☁️ Cloudflare Workers Proxy**: 100K richieste/giorno gratis, IP rotation automatica
- **🔗 n8n Webhook Integration**: Invio automatico dati a n8n per processing
- **📱 Telegram Alerts**: Notifiche real-time success/error
- **💾 Cookie Persistence**: Mantiene sessione tra esecuzioni
- **📊 Smart Price Extraction**: 6 pattern regex per estrazione prezzi affidabile
- **€0 Costi**: Completamente gratuito con free tier services

## 🏗️ Architettura

```
GitHub Actions (3x/day)
    ↓
[Playwright Browser]
    ↓
[Facebook Groups Scraper]
    ↓
[Price Extraction + Validation]
    ↓
[Cloudflare Worker Proxy] (optional)
    ↓
[n8n Webhook] → Processing
    ↓
[Telegram Notification]
```

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/bonaventuradroid/milan-social-scraper-pro.git
cd milan-social-scraper-pro
```

### 2. Setup Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Configure GitHub Secrets

Vai a Settings → Secrets and variables → Actions e aggiungi:

```
FB_EMAIL              = your_facebook_email@gmail.com
FB_PASSWORD           = your_facebook_password
FB_GROUPS             = appartamentimilano,milanoroomate
N8N_WEBHOOK           = https://bonaventura7.app.n8n.cloud/webhook/social-scrapers
CLOUDFLARE_PROXY      = (optional) https://your-worker.workers.dev
TELEGRAM_BOT_TOKEN    = (optional) your_telegram_bot_token
TELEGRAM_CHAT_ID      = (optional) your_telegram_chat_id
```

### 4. Trigger First Run

Vai a Actions → 🔄 Facebook Groups Smart Scraper → Run workflow

## 📦 Installation (Local)

```bash
pip install -r requirements.txt
python scrapers/facebook_groups.py
```

## 🔧 Configuration

### Facebook Groups

Modifica `FB_GROUPS` con i nomi dei gruppi senza `https://facebook.com/groups/`:

```env
FB_GROUPS=appartamentimilano,milanoroomate,monolocale_milano
```

### n8n Webhook

Configura il webhook nel tuo workflow n8n e aggiungi l'URL in `N8N_WEBHOOK`

### Cloudflare Worker (Optional)

Per IP rotation e anti-ban avanzato:

```bash
# Deploy a workers.dev
npm install -g wrangler
wrangler init
# Copia il codice worker da /workers/fb-proxy.js
wrangler deploy
```

## 📊 Output Format

I dati inviati al webhook n8n:

```json
{
  "listings": [
    {
      "platform": "Facebook Group",
      "title": "Monolocale Porta Romana 480€",
      "price": 480,
      "url": "https://facebook.com/groups/.../posts/...",
      "zone": "Milano",
      "type": "Monolocale",
      "scraped_at": "2025-12-05T12:49:00"
    }
  ],
  "count": 15,
  "scraped_at": "2025-12-05T12:49:00"
}
```

## 🛡️ Security

- Credenziali in GitHub Secrets (mai in repo)
- Cookie persistence in `.cache/` (in .gitignore)
- User-Agent rotation automatica
- Random delays tra richieste (anti-detection)
- Timeout e retry logic integrati

## 🐛 Troubleshooting

### Login fallisce

1. Verifica credenziali FB
2. Disabilita 2FA temporaneamente
3. Cancella `.cache/fb_cookies.json` per forzare nuovo login

### Ban da Facebook

1. Abilita Cloudflare Worker proxy
2. Aumenta delay tra richieste
3. Riduci numero di gruppi monitati
4. Usa account diversi con rotation

### Webhook n8n non riceve dati

1. Testa manualmente: `curl -X POST {WEBHOOK_URL} -H "Content-Type: application/json" -d '{"test": true}'`
2. Verifica che il webhook sia attivo in n8n
3. Controlla GitHub Actions logs

## 📈 Roadmap

- [ ] Nextdoor integration (HAR scraping)
- [ ] OCR per annunci solo immagini
- [ ] Multi-account rotation
- [ ] Rate limiting intelligente
- [ ] Dashboard monitoring
- [ ] Docker containerization

## 📝 License

MIT License - vedi [LICENSE](LICENSE) per dettagli

## ⚠️ Disclaimer

Questo tool è per uso educativo e di automazione personale. Rispetta i Terms of Service di Facebook e Nextdoor. L'autore non è responsabile per usi impropri.

---

**Creato con 💖 per la comunità tech italiana**
