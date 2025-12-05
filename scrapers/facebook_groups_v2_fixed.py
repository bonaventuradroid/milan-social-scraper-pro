#!/usr/bin/env python3
"""
🚀 Facebook Groups Scraper v2 - FIXED VERSION
FIX 1: Batch limit 200 listings per webhook
FIX 2: Retry logic (3 tentativi) con exponential backoff
FIX 3: Deduplication logic sul lato n8n (vedi DEDUP_NOTES)
FIX 4: Timeout esplicito configurato in n8n webhook
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
import logging

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from pydantic import BaseModel, Field
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# ====== CONFIG ======
FB_EMAIL = os.getenv('FB_EMAIL')
FB_PASSWORD = os.getenv('FB_PASSWORD')
FB_GROUPS = os.getenv('FB_GROUPS', 'appartamentimilano,milanoroomate').split(',')
N8N_WEBHOOK = os.getenv('N8N_WEBHOOK')
CLOUDFLARE_PROXY = os.getenv('CLOUDFLARE_PROXY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT = os.getenv('TELEGRAM_CHAT_ID')

# FIX 1: Batch limit (200 listings per webhook)
MAX_LISTINGS_PER_BATCH = 200
MAX_RETRIES = 3  # FIX 2: Retry logic
RETRY_DELAY = 2  # seconds, exponential backoff

CACHE_DIR = Path('.cache')
COOKIES_FILE = CACHE_DIR / 'fb_cookies.json'

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
    """Estrae prezzo dal testo"""
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

async def save_cookies(page):
    """Salva cookies"""
    CACHE_DIR.mkdir(exist_ok=True)
    cookies = await page.context.cookies()
    with open(COOKIES_FILE, 'w') as f:
        json.dump(cookies, f)

async def load_cookies(page):
    """Carica cookies"""
    if COOKIES_FILE.exists():
        with open(COOKIES_FILE, 'r') as f:
            cookies = json.load(f)
        await page.context.add_cookies(cookies)

async def login_facebook(page) -> bool:
    """Login con retry (FIX 2)"""
    for attempt in range(MAX_RETRIES):
        try:
            await page.goto('https://facebook.com', waitUntil='networkidle', timeout=30000)
            await page.fill('input[name="email"]', FB_EMAIL)
            await page.fill('input[name="pass"]', FB_PASSWORD)
            await page.click('button[type="submit"]')
            await page.waitForNavigation(waitUntil='networkidle', timeout=30000)
            await save_cookies(page)
            logger.info("✅ Login successful")
            return True
        except Exception as e:
            wait_time = RETRY_DELAY * (2 ** attempt)
            logger.warning(f"Login attempt {attempt+1} failed. Retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)
    return False

async def scrape_group(page, group_name: str) -> List[Listing]:
    """Scrape FB group"""
    listings = []
    try:
        url = f'https://facebook.com/groups/{group_name}'
        await page.goto(url, waitUntil='networkidle', timeout=30000)
        await page.waitForTimeout(2000)
        
        for _ in range(3):
            await page.evaluate('window.scrollBy(0, window.innerHeight)')
            await page.waitForTimeout(1500)
        
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
            except:
                continue
        
        logger.info(f"✅ {group_name}: {len(listings)} listings found")
        
    except Exception as e:
        logger.error(f"❌ Error scraping {group_name}: {e}")
    
    return listings

async def send_to_n8n_with_retry(listings: List[Listing]):
    """Invia a n8n con retry logic (FIX 2) e batch limit (FIX 1)"""
    if not N8N_WEBHOOK or not listings:
        return
    
    # FIX 1: Split into batches of max 200
    for batch_start in range(0, len(listings), MAX_LISTINGS_PER_BATCH):
        batch = listings[batch_start:batch_start + MAX_LISTINGS_PER_BATCH]
        
        for attempt in range(MAX_RETRIES):
            try:
                payload = {
                    'listings': [l.dict() for l in batch],
                    'count': len(batch),
                    'scraped_at': datetime.now().isoformat(),
                    'batch': f"{batch_start//MAX_LISTINGS_PER_BATCH + 1}"
                }
                
                session = setup_session()
                response = session.post(N8N_WEBHOOK, json=payload, timeout=30)
                response.raise_for_status()
                logger.info(f"✅ Batch {payload['batch']}: {len(batch)} listings sent to n8n")
                break  # Success
                
            except Exception as e:
                wait_time = RETRY_DELAY * (2 ** attempt)
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"❌ Send attempt {attempt+1} failed. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"❌ Failed to send after {MAX_RETRIES} attempts: {e}")

async def send_telegram(message: str):
    """Invia Telegram"""
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
    """Main scraping loop con retry logic"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.newContext(
            user_agent=USER_AGENTS[0],
            viewport={'width': 1280, 'height': 720},
        )
        page = await context.newPage()
        
        try:
            await load_cookies(page)
            
            if not await login_facebook(page):
                await send_telegram('❌ Facebook login failed after 3 retries')
                return
            
            all_listings = []
            
            for group in FB_GROUPS:
                group = group.strip()
                if group:
                    listings = await scrape_group(page, group)
                    all_listings.extend(listings)
                    await page.waitForTimeout(3000 + __import__('random').random() * 5000)
            
            if all_listings:
                await send_to_n8n_with_retry(all_listings)
                await send_telegram(f'✅ Scraped {len(all_listings)} listings successfully')
            else:
                await send_telegram('⚠️ No listings found')
            
        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(main())

# ====== DEDUP NOTES FOR n8n (FIX 4) ======
# Per eliminare duplicati nel nodo n8n "AI Merge + Scoring":
# 1. Aggiungi nodo "Code" prima di Google Sheets
# 2. Utilizza questo JavaScript:
# const seen = new Set();
# const unique = [];
# for (const listing of $input.all()) {
#   const key = `${listing.url}_${listing.price}`;
#   if (!seen.has(key)) {
#     seen.add(key);
#     unique.push(listing);
#   }
# }
# return unique;
