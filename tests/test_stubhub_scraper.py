"""
Unit tests for StubHub scraper module.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from src.stubhub_scraper import StubHubScraper, StubHubScraperError


class TestStubHubScraper:
    """Test suite for StubHub scraper."""

    def test_initialization(self):
        """Test scraper initialization."""
        scraper = StubHubScraper(request_delay=1.5, timeout=20)
        assert scraper.request_delay == 1.5
        assert scraper.timeout == 20
        assert scraper.session is not None

    def test_parse_price_valid(self):
        """Test parsing valid price strings."""
        scraper = StubHubScraper()

        # Various price formats
        assert scraper._parse_price("$150") == Decimal("150")
        assert scraper._parse_price("$1,234.56") == Decimal("1234.56")
        assert scraper._parse_price("99.99") == Decimal("99.99")
        assert scraper._parse_price("  $75.00  ") == Decimal("75.00")

    def test_parse_price_invalid(self):
        """Test parsing invalid price strings."""
        scraper = StubHubScraper()

        # Invalid formats
        assert scraper._parse_price("") is None
        assert scraper._parse_price("invalid") is None
        assert scraper._parse_price("$-10") is None  # Negative prices rejected
        assert scraper._parse_price("$0") is None  # Zero prices rejected

    def test_extract_event_id_from_url(self):
        """Test extracting event ID from StubHub URLs."""
        scraper = StubHubScraper()

        # Standard format
        url1 = "https://www.stubhub.com/event-name-tickets-12-31-2025/event/123456789/"
        assert scraper.extract_event_id_from_url(url1) == "123456789"

        # Different format
        url2 = "https://www.stubhub.com/some-path/event/987654321"
        assert scraper.extract_event_id_from_url(url2) == "987654321"

        # No event ID
        url3 = "https://www.stubhub.com/browse"
        assert scraper.extract_event_id_from_url(url3) is None

    def test_extract_prices_from_html(self):
        """Test extracting prices from HTML content."""
        scraper = StubHubScraper()

        # Sample HTML with prices
        html = """
        <html>
            <body>
                <div class="ticket-price">$150.00</div>
                <span class="Price">$200.00</span>
                <div data-testid="price">$175.50</div>
            </body>
        </html>
        """

        result = scraper._extract_prices_from_html(html)

        assert result['success'] is True
        assert result['min_price'] == Decimal("150.00")
        assert result['max_price'] == Decimal("200.00")
        assert len(result['all_prices']) == 3

    def test_extract_prices_no_prices(self):
        """Test extracting prices from HTML with no prices."""
        scraper = StubHubScraper()

        html = "<html><body><p>No tickets available</p></body></html>"

        result = scraper._extract_prices_from_html(html)

        assert result['success'] is False
        assert result.get('min_price') is None

    @patch('src.stubhub_scraper.requests.Session.get')
    def test_fetch_page_success(self, mock_get):
        """Test successful page fetching."""
        scraper = StubHubScraper()

        # Mock successful response
        mock_response = Mock()
        mock_response.text = "<html>test content</html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = scraper._fetch_page("https://www.stubhub.com/test")

        assert result == "<html>test content</html>"
        assert mock_get.called

    @patch('src.stubhub_scraper.requests.Session.get')
    def test_fetch_page_rate_limited(self, mock_get):
        """Test handling of rate limiting (429 error)."""
        scraper = StubHubScraper()

        # Mock 429 rate limit response
        import requests
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        result = scraper._fetch_page("https://www.stubhub.com/test")

        assert result is None

    @patch('src.stubhub_scraper.requests.Session.get')
    def test_fetch_page_timeout(self, mock_get):
        """Test handling of request timeout."""
        scraper = StubHubScraper()

        # Mock timeout
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()

        result = scraper._fetch_page("https://www.stubhub.com/test")

        assert result is None

    @patch.object(StubHubScraper, '_fetch_page')
    @patch.object(StubHubScraper, '_extract_prices_from_html')
    def test_scrape_event_prices_success(self, mock_extract, mock_fetch):
        """Test successful event price scraping."""
        scraper = StubHubScraper()

        # Mock responses
        mock_fetch.return_value = "<html>mock content</html>"
        mock_extract.return_value = {
            'success': True,
            'min_price': Decimal("100.00"),
            'max_price': Decimal("300.00"),
            'median_price': Decimal("150.00"),
            'all_prices': [Decimal("100.00"), Decimal("150.00"), Decimal("300.00")],
            'sections': {'Section A': Decimal("100.00")},
            'price_count': 3
        }

        url = "https://www.stubhub.com/event-name/event/123456/"
        result = scraper.scrape_event_prices(url)

        assert result['success'] is True
        assert result['min_price'] == Decimal("100.00")
        assert result['source'] == 'stubhub'
        assert result['url'] == url

    def test_scrape_event_prices_invalid_url(self):
        """Test scraping with invalid URL."""
        scraper = StubHubScraper()

        url = "https://www.ticketmaster.com/event/123"
        result = scraper.scrape_event_prices(url)

        assert result['success'] is False
        assert 'Not a StubHub URL' in result['error']

    @patch.object(StubHubScraper, '_fetch_page')
    def test_scrape_event_prices_fetch_failure(self, mock_fetch):
        """Test scraping when page fetch fails."""
        scraper = StubHubScraper()

        mock_fetch.return_value = None

        url = "https://www.stubhub.com/event/123"
        result = scraper.scrape_event_prices(url)

        assert result['success'] is False
        assert result['error'] == 'Failed to fetch page'

    @patch.object(StubHubScraper, '_fetch_page')
    @patch.object(StubHubScraper, '_extract_prices_from_html')
    def test_scrape_event_prices_no_prices_found(self, mock_extract, mock_fetch):
        """Test scraping when no prices are found."""
        scraper = StubHubScraper()

        mock_fetch.return_value = "<html>mock content</html>"
        mock_extract.return_value = {
            'success': False,
            'min_price': None,
            'error': 'No prices found'
        }

        url = "https://www.stubhub.com/event/123"
        result = scraper.scrape_event_prices(url)

        assert result['success'] is False
        assert 'No prices found' in result.get('error', '')

    def test_respect_delay(self):
        """Test that request delay is respected."""
        import time
        scraper = StubHubScraper(request_delay=0.1)

        # First request should not delay
        start = time.time()
        scraper._respect_delay()
        elapsed1 = time.time() - start
        assert elapsed1 < 0.05  # Should be almost immediate

        # Second request should delay
        start = time.time()
        scraper._respect_delay()
        elapsed2 = time.time() - start
        assert elapsed2 >= 0.08  # Should wait ~0.1 seconds

    def test_random_user_agent(self):
        """Test user agent rotation."""
        scraper = StubHubScraper()

        user_agents = [scraper._get_random_user_agent() for _ in range(10)]

        # Should get user agents from the list
        assert all(ua in StubHubScraper.USER_AGENTS for ua in user_agents)

        # Should have some variety (not all the same)
        assert len(set(user_agents)) > 1

    def test_close(self):
        """Test scraper cleanup."""
        scraper = StubHubScraper()

        # Should not raise an exception
        scraper.close()

        # Session should be closed
        # (We can't easily test this without implementation details)

    def test_test_scraping(self):
        """Test the test_scraping convenience method."""
        scraper = StubHubScraper()

        with patch.object(scraper, 'scrape_event_prices') as mock_scrape:
            # Test success
            mock_scrape.return_value = {'success': True}
            assert scraper.test_scraping("https://stubhub.com/event/123") is True

            # Test failure
            mock_scrape.return_value = {'success': False}
            assert scraper.test_scraping("https://stubhub.com/event/123") is False

            # Test exception
            mock_scrape.side_effect = Exception("Test error")
            assert scraper.test_scraping("https://stubhub.com/event/123") is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
