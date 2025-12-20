import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def is_spa_or_dynamic(html: str) -> bool:
    """Check if page is likely a SPA or uses dynamic content"""
    spa_indicators = [
        '<app-root',           # Angular
        'id="root"',           # React
        'id="app"',            # Vue
        'ng-app',              # AngularJS
        'data-reactroot',      # React
        'v-app',               # Vue
        '<script>window.__INITIAL_STATE__'  # Redux/state
    ]
    return any(indicator in html for indicator in spa_indicators)

def scrape_with_requests(url: str) -> str:
    """Try simple scraping first (faster)"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    return r.text

def scrape_with_selenium(url: str) -> str:
    """Use Selenium for dynamic content"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        driver.get(url)
        
        # Wait for content
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Extra wait for dynamic content
        time.sleep(3)
        
        return driver.page_source
        
    finally:
        driver.quit()

def scrape_jd(url: str) -> str:
    """Smart scraper: tries requests first, falls back to Selenium"""
    
    try:
        # Try fast method first
        print("🔄 Trying fast scraping...")
        html = scrape_with_requests(url)
        
        # Check if it's a SPA
        if is_spa_or_dynamic(html):
            print("⚠️  Detected SPA/dynamic content, using Selenium...")
            html = scrape_with_selenium(url)
        else:
            print("✓ Static site detected, fast scraping successful")
            
    except Exception as e:
        print(f"⚠️  Fast scraping failed: {e}")
        print("🔄 Falling back to Selenium...")
        html = scrape_with_selenium(url)
    
    # Save raw HTML
    with open("scraped_raw.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✓ Saved raw HTML to scraped_raw.html")
    
    # Parse HTML
    soup = BeautifulSoup(html, "lxml")
    
    # Remove junk
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "iframe"]):
        tag.decompose()
    
    # Extract meaningful text
    text = soup.get_text(separator="\n")
    lines = []
    capture = False
    
    for line in text.splitlines():
        line = line.strip()
        
        if not line or len(line) < 15:
            continue
        
        line_lower = line.lower()
        
        # Start capturing at JD sections
        if any(marker in line_lower for marker in [
            "about the position", "job description", "what you'll do",
            "what you will do", "responsibilities", "requirements",
            "qualifications", "expertise", "skills required"
        ]):
            capture = True
            print(f"✓ Found JD section: {line[:50]}")
        
        # Skip navigation/footer
        if any(skip in line_lower for skip in [
            "copyright", "privacy policy", "cookie", "follow us",
            "all rights reserved", "terms of service"
        ]):
            continue
        
        # Capture relevant lines
        if capture or any(keyword in line_lower for keyword in [
            "javascript", "react", "angular", "vue", "python", "java",
            "typescript", "html", "css", "node", "framework", "api",
            "experience", "developer", "engineer", "years", "must have"
        ]):
            lines.append(line)
    
    # Fallback if too little content
    if len(lines) < 20:
        print("⚠️  Got too few lines, using fallback extraction")
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if len(line) > 25:
                lines.append(line)
    
    result = "\n".join(lines[:200])
    
    # Save result
    with open("scraped_jd.txt", "w", encoding="utf-8") as f:
        f.write(result)
    
    print(f"\n✓ Scraped {len(lines)} lines")
    print("\n=== SCRAPED JD (first 800 chars) ===")
    print(result)
    print("\n====================================\n")
    
    if len(result) < 200:
        print("⚠️  WARNING: Very little content extracted!")
    
    return result