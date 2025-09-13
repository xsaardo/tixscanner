"""
Optimized Chrome options for Ticketmaster scraping.

Based on testing, this configuration provides the best balance of:
- Speed and efficiency
- Anti-detection capabilities  
- Reliable price extraction
"""

def get_optimized_chrome_options():
    """
    Get optimized Chrome options for Ticketmaster scraping.
    
    Returns:
        Chrome Options object with optimal settings
    """
    from selenium.webdriver.chrome.options import Options
    
    options = Options()
    
    # === CORE BROWSER SETTINGS ===
    options.add_argument("--headless")  # No GUI (faster)
    options.add_argument("--window-size=1920,1080")  # Realistic desktop resolution
    
    # === PERFORMANCE OPTIMIZATIONS ===
    options.add_argument("--disable-images")  # Major speed boost for price scraping
    options.add_argument("--disable-gpu")  # More stable in headless mode
    options.add_argument("--disable-dev-shm-usage")  # Docker/container compatibility
    options.add_argument("--disable-extensions")  # Faster startup
    options.add_argument("--disable-plugins")  # Remove variables
    
    # === ANTI-DETECTION (Advanced) ===
    # These are the most important for bypassing bot detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # === REALISTIC BROWSER SIMULATION ===
    # Updated user agent to match current Chrome version
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.7258.154 Safari/537.36")
    
    # === JAVASCRIPT STRATEGY ===
    # Based on testing, JS can be disabled for Ticketmaster since pricing is server-rendered
    # But we'll make it configurable:
    # options.add_argument("--disable-javascript")  # Uncomment for speed boost
    
    # === MEMORY & RESOURCE MANAGEMENT ===
    options.add_argument("--memory-pressure-off")
    options.add_argument("--max_old_space_size=4096")
    
    # === ADDITIONAL STEALTH OPTIONS ===
    # These help avoid detection patterns
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--disable-ipc-flooding-protection")
    
    return options

def get_minimal_chrome_options():
    """
    Get minimal Chrome options for maximum speed.
    Use when you need fastest possible scraping.
    """
    from selenium.webdriver.chrome.options import Options
    
    options = Options()
    
    # Absolute minimal for speed
    options.add_argument("--headless")
    options.add_argument("--disable-images")
    options.add_argument("--disable-javascript")  # Maximum speed
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    
    return options

def get_stealth_chrome_options():
    """
    Get maximum stealth Chrome options.
    Use when anti-bot detection is very aggressive.
    """
    from selenium.webdriver.chrome.options import Options
    
    options = Options()
    
    # Core settings
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    
    # Maximum stealth
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Realistic browser behavior
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values": {
            "notifications": 2,  # Block notifications
            "geolocation": 2,    # Block location requests
        }
    })
    
    # Performance (but not aggressive)
    options.add_argument("--disable-images")
    options.add_argument("--disable-gpu")
    
    # Latest realistic user agent
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.7258.154 Safari/537.36")
    
    return options

# Usage recommendations:
"""
🚀 SPEED PRIORITY (Current working approach):
use get_minimal_chrome_options() - Fastest, works with Ticketmaster

🎭 STEALTH PRIORITY (If detection increases):  
use get_stealth_chrome_options() - Maximum anti-detection

⚖️ BALANCED (Recommended for production):
use get_optimized_chrome_options() - Good balance of speed and stealth
"""