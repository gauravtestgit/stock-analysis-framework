import time
from collections import defaultdict

class RateLimitTracker:
    def __init__(self):
        self.request_count = 0
        self.rate_limit_errors = 0
        self.all_errors = []
        self.request_times = []
        self.ticker_requests = defaultdict(int)
        self.error_patterns = defaultdict(int)
    
    def track_request(self, ticker=""):
        self.request_count += 1
        current_time = time.time()
        self.request_times.append(current_time)
        if ticker:
            self.ticker_requests[ticker] += 1
        
        if self.request_count % 10 == 0:
            recent_rate = self._calculate_recent_rate()
            print(f"🔄 YFinance: {self.request_count} requests, Rate: {recent_rate:.1f}/min, Errors: {self.rate_limit_errors}")
    
    def check_rate_limit_error(self, error_msg: str, ticker: str = ""):
        # Log all errors for analysis
        self.all_errors.append(f"{ticker}: {error_msg}")
        self.error_patterns[error_msg.lower()[:50]] += 1  # Track error patterns
        
        # Check for rate limit indicators
        rate_limit_indicators = ['too many requests', '429', 'rate limit', 'throttle', 'quota exceeded', 'monthly limit', 'daily limit']
        if any(indicator in error_msg.lower() for indicator in rate_limit_indicators):
            self.rate_limit_errors += 1
            print(f"⚠️ RATE LIMIT: YFinance rate limit detected! Total: {self.rate_limit_errors}")
            print(f"   Ticker: {ticker}, Error: {error_msg}")
        else:
            # Check for internal throttling patterns
            throttle_patterns = ['no data found', 'possibly delisted', 'quote not found', 'connection', 'timeout']
            if any(pattern in error_msg.lower() for pattern in throttle_patterns):
                recent_rate = self._calculate_recent_rate()
                print(f"🔍 YFinance Error ({ticker}) [Rate: {recent_rate:.1f}/min]: {error_msg}")
            else:
                print(f"🔍 YFinance Error ({ticker}): {error_msg}")
    
    def get_error_summary(self):
        return {
            'total_requests': self.request_count,
            'rate_limit_errors': self.rate_limit_errors,
            'all_errors': self.all_errors[-10:],  # Last 10 errors
            'request_rate_per_min': self._calculate_recent_rate(),
            'top_error_patterns': dict(sorted(self.error_patterns.items(), key=lambda x: x[1], reverse=True)[:5]),
            'ticker_request_counts': dict(self.ticker_requests)
        }
    
    def _calculate_recent_rate(self):
        """Calculate requests per minute for last 60 seconds"""
        if not self.request_times:
            return 0.0
        
        current_time = time.time()
        recent_requests = [t for t in self.request_times if current_time - t <= 60]
        return len(recent_requests)

    def print_analysis(self):
        """Print detailed analysis of request patterns"""
        print("\n📊 YFinance Request Analysis:")
        print(f"Total Requests: {self.request_count}")
        print(f"Current Rate: {self._calculate_recent_rate():.1f} requests/minute")
        print(f"Rate Limit Errors: {self.rate_limit_errors}")
        print(f"Other Errors: {len(self.all_errors) - self.rate_limit_errors}")
        
        if self.error_patterns:
            print("\nTop Error Patterns:")
            for pattern, count in sorted(self.error_patterns.items(), key=lambda x: x[1], reverse=True)[:3]:
                print(f"  • {pattern}: {count} times")
        
        if self.ticker_requests:
            failed_tickers = [ticker for ticker, count in self.ticker_requests.items() if count > 1]
            if failed_tickers:
                print(f"\nTickers with multiple requests (potential retries): {failed_tickers}")

# Global instance
rate_tracker = RateLimitTracker()