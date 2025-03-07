import asyncio
import aiohttp
import ssl
from bs4 import BeautifulSoup
import logging
import json
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_login():
    # Create SSL context that doesn't verify certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://mydewarmte.com",
        "Referer": "https://mydewarmte.com/"
    }
    
    conn = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=conn) as session:
        # Get the login page to get CSRF token
        logger.info("Getting login page...")
        async with session.get("https://mydewarmte.com/", headers=headers) as response:
            if response.status != 200:
                logger.error("Failed to get login page: %d", response.status)
                return
            
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")
            
            # Get CSRF token
            csrf_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
            if not csrf_input:
                logger.error("Could not find CSRF token")
                return
                
            csrf_token = csrf_input.get("value")
            logger.info("Found CSRF token: %s", csrf_token)
            
            # Add CSRF token to headers
            headers["X-CSRFToken"] = csrf_token
            
            # Prepare login data
            login_data = {
                "username": "mail@ronaldwillems.nl",  # Form uses username field
                "password": "7mb87yba",
                "csrfmiddlewaretoken": csrf_token
            }
            
            # Submit the login form
            logger.info("Attempting login...")
            async with session.post(
                "https://mydewarmte.com/",
                data=login_data,
                headers=headers,
                allow_redirects=True
            ) as login_response:
                logger.info("Login response status: %d", login_response.status)
                logger.info("Login response URL: %s", str(login_response.url))
                response_text = await login_response.text()
                logger.info("Login response content: %s", response_text[:500])
                
                # If login successful, try to access dashboard
                if "dashboard" in str(login_response.url):
                    logger.info("Login successful, accessing dashboard...")
                    async with session.get("https://mydewarmte.com/dashboard", headers=headers) as dashboard_response:
                        logger.info("Dashboard response status: %d", dashboard_response.status)
                        dashboard_html = await dashboard_response.text()
                        logger.info("Dashboard content: %s", dashboard_html[:500])
                        
                        # Parse dashboard data
                        dashboard_soup = BeautifulSoup(dashboard_html, "html.parser")
                        for div in dashboard_soup.find_all("div", class_=True):
                            logger.info("Found div with classes: %s", div["class"])
                            logger.info("Content: %s", div.get_text().strip())
                            logger.info("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_login()) 