#!/usr/bin/env python3
"""
🚀 Smart Facebook Groups Scraper con Anti-Ban
Integrazione n8n webhook + Cloudflare proxy + Cookie persistence
"""

import os
import json
import time
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import asyncio

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from pydantic import BaseModel, Field
from playwright.async_api import async_playwright, Page, Browser
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ====== CONFIG ======
FB_EMAIL = os.getenv('FB_EMAIL')
FB_PASSWORD = os.getenv('FB_PASSWORD')
FB_GROUPS = os.getenv('FB_GROUPS', 'appartamentimilano,milanoroomate').split(',')
N8N_WEBHOOK = os.getenv('N8N_WEBHOOK')
CLOUDFLARE_PROXY = os.getenv('CLOUDFLARE_PROXY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT = os.getenv('TELEGRAM_CHAT_ID')

CACHE_DIR = Path('.cache')
COOKIES_FILE = CACHE_DIR / 'fb_cookies.json'
LOGS_DIR = Path('.logs')

# User agents per anti-ban
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
]

PRICE_PATTERNS = [
    r'€\s*(\d{3,4})',
    r'(\d{3,4})\s*€',
    r'euro\s*(\d{3,4})',
    r'(\d{3,4})\s*euro',
    r'prezzo?\s*€?\s*(\d{3,4})',
]

class Listing(BaseModel):
    platform: str = "Facebook Group"
    title: str
    price: int = Field(gt=100, lt=5000)
    url: str
    zone: str = "Milano"
    type: str = "Monolocale"
    scraped_at: datetime = Field(default_factory=datetime.now)

    def dict(self, **kwargs):
        data = super().dict(**kwargs)
        data['scraped_at'] = data['scraped_at'].isoformat()
        return data

def setup_session():
    """Setup requests session con retry logic"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def extract_price(text: str) -> Optional[int]:
    """Estrae prezzo dal testo con pattern matching"""
    for pattern in PRICE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                price = int(match.group(1) if '(' in pattern else match.group(0).replace('€', '').replace('euro', '').strip())
                if 200 <= price <= 2000:
                    return price
            except:
                pass
    return None

async def save_cookies(page: Page):
    """Salva cookies per sessione persistente"""
    CACHE_DIR.mkdir(exist_ok=True)
    cookies = await page.context.cookies()
    with open(COOKIES_FILE, 'w') as f:
        json.dump(cookies, f)

async def load_cookies(page: Page):
    """Carica cookies salvati"""
    if COOKIES_FILE.exists():
        with open(COOKIES_FILE, 'r') as f:
            cookies = json.load(f)
        await page.context.add_cookies(cookies)

async def login_facebook(page: Page) -> bool:
    """Login Facebook con retry"""
    try:
        await page.goto('https://facebook.com', waitUntil='networkidle', timeout=30000)
        time.sleep(2 + __import__('random').random() * 3)
        
        await page.fill('input[name="email"]', FB_EMAIL)
        await page.fill('input[name="pass"]', FB_PASSWORD)
        await page.click('button[type="submit"]')
        await page.waitForNavigation(waitUntil='networkidle', timeout=30000)
        
        # Salva cookies dopo login
        await save_cookies(page)
        return True
    except Exception as e:
        print(f"❌ Login fallito: {e}")
        return False

async def scrape_group(page: Page, group_name: str) -> List[Listing]:
    """Scrape singolo FB Group"""
    listings = []
    try:
        url = f'https://facebook.com/groups/{group_name}'
        await page.goto(url, waitUntil='networkidle', timeout=30000)
        await page.waitForTimeout(2000 + __import__('random').random() * 3000)
        
        # Scroll per caricare post
        for _ in range(3):
            await page.evaluate('window.scrollBy(0, window.innerHeight)')
            await page.waitForTimeout(1500)
        
        # Estrai posts
        posts = await page.evaluate('''
            Array.from(document.querySelectorAll('[role="article"]')).slice(0, 50).map(post => ({
                text: post.innerText,
                href: post.querySelector('a') ? post.querySelector('a').href : '',
            }))
        ''')
        
        for post in posts:
            try:
                price = extract_price(post['text'])
                if price:
                    listing = Listing(
                        title=post['text'][:100],
                        price=price,
                        url=post.get('href', f'https://facebook.com/groups/{group_name}'),
                    )
                    listings.append(listing)
            except Exception as e:
                continue
        
        print(f"✅ {group_name}: {len(listings)} annunci trovati")
        
    except Exception as e:
        print(f"❌ Errore scraping {group_name}: {e}")
    
    return listings

async def send_to_n8n(listings: List[Listing]):
    """Invia dati al webhook n8n"""
    if not N8N_WEBHOOK or not listings:
        return
    
    try:
        payload = {
            'listings': [l.dict() for l in listings],
            'scraped_at': datetime.now().isoformat(),
            'count': len(listings)
        }
        
        # Usa Cloudflare proxy se configurato
        url = CLOUDFLARE_PROXY if CLOUDFLARE_PROXY else N8N_WEBHOOK
        if CLOUDFLARE_PROXY:
            url += f'?url={N8N_WEBHOOK}'
        
        session = setup_session()
        response = session.post(url, json=payload, timeout=30)
        response.raise_for_status()
        print(f"✅ n8n webhook: {len(listings)} listings inviati")
    except Exception as e:
        print(f"❌ Errore invio n8n: {e}")

async def send_telegram(message: str):
    """Invia notifica Telegram"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        return
    
    try:
        requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            data={'chat_id': TELEGRAM_CHAT, 'text': message},
            timeout=10
        )
    except:
        pass

async def main():
    """Main scraping loop"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.newContext(
            user_agent=USER_AGENTS[0],
            viewport={'width': 1280, 'height': 720},
        )
        page = await context.newPage()
        
        try:
            # Carica cookies se esistono
            await load_cookies(page)
            
            # Prova login
            if not await login_facebook(page):
                await send_telegram('❌ Facebook login fallito')
                return
            
            all_listings = []
            
            # Scrape tutti i gruppi
            for group in FB_GROUPS:
                group = group.strip()
                if group:
                    listings = await scrape_group(page, group)
                    all_listings.extend(listings)
                    # Anti-ban: delay random
                    await page.waitForTimeout(3000 + __import__('random').random() * 5000)
            
            # Invia a n8n
            if all_listings:
                await send_to_n8n(all_listings)
                await send_telegram(f'✅ Scraped {len(all_listings)} listings')
            else:
                await send_telegram('⚠️ No listings found')
            
        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
