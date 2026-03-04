# StubHub Support Investigation

**Issue:** #2 - Investigate StubHub as a ticket source
**Date:** 2026-03-03
**Status:** Investigation Complete

## Executive Summary

StubHub offers both an official API and web scraping as potential integration options for TixScanner. While the API provides structured, reliable data access, it requires manual approval and has rate limits. Web scraping is technically feasible but faces significant anti-bot challenges and potential ToS violations.

**Recommendation:** Pursue official API access as the primary approach, with web scraping as a technical fallback only if API access is granted but pricing data is limited.

## 1. StubHub API Overview

### 1.1 Official API Availability

StubHub provides a comprehensive REST API documented at [developer.stubhub.com](https://developer.stubhub.com/).

**Access Requirements:**
- **Manual Approval Required**: No self-service API access
- **Contact Points:**
  - Buyer/affiliate apps: affiliates@stubhub.com
  - Seller-focused apps: api.support@stubhub.com
- **Processing Time**: High volume of requests; prioritized based on customer impact
- **Cost**: Not publicly disclosed; likely requires partnership or agreement

### 1.2 Authentication

**OAuth2 Required:**
- All API requests must be authenticated
- Two authentication flows available:
  1. **Application-Only Flow**: Access to public data (events, listings)
  2. **User-Login Flow**: Access to user-specific data (purchases, sales)
- Unauthenticated requests return `401 Unauthorized`

### 1.3 Available API Endpoints

#### Catalog API (Public Event Data)

**Event Search & Discovery:**
- `GET /catalog/events` - List all events with filtering
  - Pagination: `page` and `page_size` parameters
  - Filtering: by country, genre, date, geographic location
  - Updated since timestamp for syncing
- `GET /catalog/events/{eventId}` - Get detailed event information
- `GET /catalog/categories/{categoryId}/events` - Events by category
- `PUT /catalog/events` - Get multiple events by IDs (batch retrieval)

**Venue Information:**
- `GET /catalog/venues` - List venues
- `GET /catalog/venues/{venueId}` - Get venue details

**Inventory/Pricing:**
- `GET /search/inventory/v2` - Search ticket listings for an event
  - Returns: ticket prices, seat sections/rows, quantity, delivery methods
  - **Limitation**: Maximum 250 listings per query (requires pagination)
  - **Access Note**: Requires explicit subscription; "All APIs" access doesn't include inventory search

#### Response Format

- Content-Type: `application/hal+json` (HAL - Hypertext Application Language)
- Includes embedded resources and hypermedia links
- Structured JSON with comprehensive metadata

### 1.4 Rate Limits

**Free Tier Restrictions:**
- **10 requests per minute** for the free API tier
- **Impact**: For monitoring multiple events, this severely limits check frequency
  - Example: 2 API calls per event = ~5 events per minute
  - Daily summary for 20+ events could take extended time

**Comparison to Ticketmaster:**
- Ticketmaster: 5,000 requests/day
- StubHub: ~14,400 requests/day (10/min × 60 min × 24 hours)
- **Note**: This is theoretically higher but distributed differently

### 1.5 Data Availability

**Event Data:**
- Event name, date, time
- Venue details (name, location, capacity)
- Categories and genres
- Event status and availability

**Pricing Data:**
- Current ticket prices (min/max ranges)
- Face value vs. resale prices
- Section-specific pricing
- Quantity available per listing
- Seller ratings and delivery options

**Limitations:**
- Inventory API requires special access
- Real-time availability may have delays
- Historical pricing not readily available (would need to track)

## 2. Web Scraping Analysis

### 2.1 Technical Feasibility

**Scraping Difficulty: HIGH**

StubHub employs enterprise-grade anti-bot protection making scraping extremely challenging.

#### Anti-Bot Protection Stack

1. **Akamai Bot Manager**
   - Device fingerprinting
   - Behavior analysis
   - Machine learning detection

2. **PerimeterX/DataDome**
   - Behavioral biometrics
   - Mouse movement tracking
   - Typing pattern analysis
   - TLS fingerprinting

3. **Cloudflare Protection**
   - JavaScript challenges
   - CAPTCHA deployment
   - Real-time behavior analysis

4. **Rate Limiting & IP Blocking**
   - Per-session request limits
   - Datacenter IP blacklisting
   - Immediate 403 errors on detection

### 2.2 Technical Architecture Challenges

**Modern Frontend Stack:**
- Built on React and Next.js
- Heavy client-side rendering
- Data not available in initial HTML
- Requires full DOM hydration
- Dynamic content loading via AJAX

**Requirements for Success:**
- Full JavaScript execution (headless browser)
- Residential proxy rotation (datacenter IPs blocked)
- Human-like behavior simulation
- Random timing delays
- Session management and cookie handling

### 2.3 Scraping Implementation Approaches

#### Option A: Headless Browser Automation

**Tools:** Playwright, Puppeteer, Selenium
**Advantages:**
- Handles JavaScript rendering
- Can execute like real browser
- Supports cookies and session management

**Disadvantages:**
- Resource-intensive (CPU, memory)
- Slower than API calls
- Detectable browser fingerprints
- Requires sophisticated anti-detection measures

#### Option B: API Interception

**Approach:** Capture internal JSON API calls
**Advantages:**
- Cleaner, structured data
- Faster than HTML parsing
- More reliable data extraction

**Disadvantages:**
- Still requires browser automation
- Internal APIs may change frequently
- Still subject to anti-bot detection

#### Option C: Third-Party Scraping Services

**Examples:** Bright Data, Apify, ScraperAPI
**Advantages:**
- Handle proxy rotation and anti-bot evasion
- Maintained scraping infrastructure
- Better success rates

**Disadvantages:**
- **Cost**: $100-500+/month for reliable service
- External dependency
- Data privacy concerns
- May still face blocks

### 2.4 Extractable Data (If Scraping Succeeds)

- Event names, dates, venues
- Ticket pricing by section
- Seat location (section, row, seat)
- Quantity available
- Seller ratings
- Delivery methods
- Real-time inventory updates

## 3. Terms of Service & Legal Considerations

### 3.1 User Agreement Prohibitions

**Automated Access:**
- StubHub's User Agreement explicitly prohibits "use of automated devices or programs"
- Bot scripts and brute force attacks result in IP blacklisting
- Violating ToS could result in legal action

### 3.2 Robots.txt Restrictions

**Disallowed Paths:**
- `/secure/` - Secure user sections
- `/AjaxService/` - AJAX backend services
- `/landingpage/` - Landing pages
- `/help/privacy/`, `/help/cookies/` - Privacy documentation

**Interpretation:**
- Primary event listing pages are not explicitly disallowed
- However, aggressive scraping of any content is discouraged
- robots.txt is more about search engines; ToS covers all automated access

### 3.3 Legal Risk Assessment

**Risk Level: MODERATE to HIGH**

1. **Contract Violation**: Scraping violates StubHub's User Agreement
2. **Computer Fraud**: Aggressive scraping could trigger CFAA (Computer Fraud and Abuse Act) concerns
3. **IP Ban**: Technical consequence rather than legal
4. **Cease & Desist**: Possibility of legal notice

**Mitigating Factors:**
- Scraping publicly visible pricing (not user accounts)
- Low-frequency requests (not DDoS-level)
- Personal use (single user application)

**Note:** This is not legal advice. Consult with legal counsel for specific guidance.

## 4. Integration Architecture Recommendations

### 4.1 Recommended Approach: Official API (Primary)

**Implementation Steps:**

1. **Apply for API Access**
   - Contact: affiliates@stubhub.com
   - Describe: Price monitoring tool for ticket buyers
   - Emphasize: Consumer benefit, driving ticket sales

2. **Design Data Model**
   ```python
   # Extend existing models to support multi-source tracking
   class TicketSource(Enum):
       TICKETMASTER = "ticketmaster"
       STUBHUB = "stubhub"

   class Concert:
       event_id: str
       source: TicketSource  # New field
       source_specific_id: str  # Platform-specific ID
       # ... existing fields
   ```

3. **Create StubHub API Client**
   ```python
   # src/stubhub_api.py
   class StubHubAPI:
       def __init__(self, client_id, client_secret):
           # OAuth2 authentication
           # Rate limiting (10 req/min)
           # Caching (30 min like Ticketmaster)

       def get_event_details(self, event_id):
           # GET /catalog/events/{eventId}

       def get_ticket_inventory(self, event_id):
           # GET /search/inventory/v2
           # Handle 250 listing pagination
   ```

4. **Update Price Monitor**
   - Add source selection logic
   - Handle multi-source price comparison
   - Unified price alert system

5. **Configuration Updates**
   ```ini
   [api]
   ticketmaster_key = ...
   stubhub_client_id = ...
   stubhub_client_secret = ...

   [concerts]
   # Format: source:event_id = threshold
   ticketmaster:1700630C79D40EAD = 500.00
   stubhub:103456789 = 300.00
   ```

**Advantages:**
- Reliable, structured data
- Terms of Service compliant
- Sustainable long-term solution
- Better data accuracy

**Challenges:**
- Approval required (may be denied)
- Rate limits (10 req/min)
- Potential API costs
- Additional complexity

### 4.2 Alternative Approach: Web Scraping (Fallback)

**Only Pursue If:**
- Official API access is denied AND
- User accepts ToS violation risks AND
- Budget exists for proxy/scraping services

**Implementation Requirements:**

1. **Scraping Infrastructure**
   - Selenium/Playwright with undetected-chromedriver
   - Residential proxy service (rotating IPs)
   - CAPTCHA solving service (if needed)
   - Robust error handling and retry logic

2. **Respectful Scraping Practices**
   - Rate limiting: Max 1 request per 30 seconds per event
   - Random delays: 15-60 seconds between requests
   - Off-peak hours: Run checks during low-traffic times
   - User-Agent rotation: Mimic real browsers

3. **Maintenance Burden**
   - HTML structure changes require updates
   - Anti-bot measures evolve over time
   - Higher failure rate than API
   - Ongoing monitoring required

**Cost Estimate:**
- Proxy service: $50-200/month (residential IPs)
- CAPTCHA solving: $1-3 per 1000 CAPTCHAs
- Development time: 20-40 hours initial + 5-10 hours/month maintenance

### 4.3 Hybrid Approach

**Strategy:**
1. Use API for event discovery and basic info
2. Supplement with scraping for detailed pricing (if API insufficient)
3. Cache aggressively to minimize requests
4. Fall back gracefully when scraping fails

## 5. Comparison: Ticketmaster vs. StubHub

| Feature | Ticketmaster | StubHub |
|---------|-------------|---------|
| **API Access** | Self-service, free tier | Manual approval required |
| **Rate Limits** | 5,000 req/day | 10 req/min (14,400/day theoretical) |
| **Authentication** | API key only | OAuth2 required |
| **Pricing Data** | Primary sale prices | Resale market prices |
| **Data Freshness** | Real-time | Real-time |
| **API Stability** | High | High |
| **Scraping Difficulty** | Moderate | Very High |
| **ToS Compliance** | API allowed | API allowed, scraping prohibited |
| **Cost** | Free | Unknown (likely free or partnership) |
| **Integration Effort** | Low (already done) | Moderate |

## 6. Next Steps & Recommendations

### 6.1 Immediate Actions

1. **Apply for API Access** (DO THIS FIRST)
   - Email: affiliates@stubhub.com
   - Subject: "API Access Request - Ticket Price Monitoring Application"
   - Include: TixScanner description, use case, consumer benefit
   - Timeline: 2-4 weeks for response (possibly longer)

2. **Await API Response**
   - If approved: Proceed with API integration (Recommendation 6.2)
   - If denied: Re-evaluate need for StubHub support

3. **Do NOT Implement Scraping Without:**
   - Legal review of ToS implications
   - User acceptance of risks
   - Budget for required services

### 6.2 If API Access Granted

**Implementation Priority:**

**Phase 1: Basic Integration** (Week 1-2)
- [ ] Implement OAuth2 authentication
- [ ] Create StubHubAPI client class
- [ ] Add event search functionality
- [ ] Test API connectivity and rate limits

**Phase 2: Price Monitoring** (Week 2-3)
- [ ] Extend data models for multi-source support
- [ ] Implement inventory/pricing retrieval
- [ ] Add StubHub to price monitoring loop
- [ ] Handle pagination for large events (250 listing limit)

**Phase 3: User Configuration** (Week 3-4)
- [ ] Update config.ini format for multi-source
- [ ] Modify email templates for source indication
- [ ] Add source filtering to price alerts
- [ ] Update documentation

**Phase 4: Testing & Refinement** (Week 4-5)
- [ ] Test with real StubHub events
- [ ] Optimize rate limit handling
- [ ] Implement intelligent caching
- [ ] Monitor API usage statistics

### 6.3 If API Access Denied

**Options:**

1. **Accept Limitation**: TixScanner remains Ticketmaster-only
   - Pros: Simple, compliant, no additional costs
   - Cons: Misses StubHub resale market data

2. **Manual Event Lookup**: Users manually check StubHub
   - Pros: No technical/legal issues
   - Cons: Defeats automation purpose

3. **Scraping (High Risk)**: Implement web scraping
   - Pros: Technical capability to get data
   - Cons: ToS violation, high maintenance, costly, risky

**Recommendation:** If API denied, remain Ticketmaster-only unless StubHub becomes critical to user needs.

## 7. Conclusion

StubHub integration is **technically feasible** through their official API but **requires manual approval**. Web scraping is **possible but not recommended** due to:

- Strong anti-bot protections
- ToS violations
- High maintenance burden
- Significant infrastructure costs

**Primary Recommendation:**
1. Apply for official API access
2. If approved, implement API integration using phased approach
3. If denied, accept Ticketmaster-only limitation
4. **Do NOT pursue web scraping** unless user explicitly accepts risks and costs

**Key Success Factors:**
- Clear value proposition in API access request
- Emphasis on consumer benefit and StubHub sales
- Professional implementation with rate limit respect
- Willingness to establish partnership if required

---

## Appendix A: API Access Request Template

```
Subject: API Access Request - Ticket Price Monitoring Application

Dear StubHub API Team,

I am developing TixScanner, a personal ticket price monitoring application that helps
concert-goers track ticket prices and receive alerts when prices drop below their budget.

TixScanner currently monitors Ticketmaster events and I would like to expand support to
include StubHub's resale marketplace, providing users with comprehensive price visibility
across primary and secondary markets.

Application Details:
- Purpose: Personal ticket price tracking and email alerts
- Use Case: Monitor specific events, alert on price drops
- Frequency: ~10-20 events, checked every 2 hours
- Target Data: Event details, ticket inventory, pricing
- User Base: Single user (personal project, potential for expansion)

This integration would benefit StubHub by:
- Driving ticket awareness and sales
- Providing price transparency to buyers
- Encouraging purchases when prices reach user thresholds

I am requesting access to:
- Catalog API (event search and details)
- Inventory Search API (ticket listings and pricing)

Thank you for considering this request. I am happy to provide additional information
or discuss partnership opportunities.

Best regards,
[Your Name]
[Contact Information]
```

## Appendix B: Useful Resources

- **StubHub Developer Portal**: https://developer.stubhub.com/
- **API Documentation**: https://developer.stubhub.com/api-reference/catalog/
- **Authentication Guide**: https://developer.stubhub.com/docs/authentication/
- **Example Implementation**: https://gist.github.com/ozzieliu/9fbbc83b354c568709dc4e6a30fea54f
- **Contact**: affiliates@stubhub.com

---

**Investigation completed:** 2026-03-03
**Investigator:** Claude (AI Assistant)
**Next Review:** Upon API access response
