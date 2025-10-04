#!/usr/bin/env python3
"""
Quick test for browser collectors JSON parse error fix
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv('.env')

from browser_collectors import BrowserDataCollectionService

def test_browser_collectors():
    """Test that JSON errors are handled gracefully"""
    print("=" * 80)
    print("Testing Browser Collectors - JSON Error Handling")
    print("=" * 80)
    
    country_code = 'FR'
    print(f"\nTesting with {country_code}...")
    
    try:
        service = BrowserDataCollectionService(region=os.getenv('AWS_REGION', 'us-west-2'))
        
        # This will attempt browser collection, and fall back to mock data if it fails
        country_data = service.collect_country_data(
            country_code=country_code,
            max_news=3
        )
        
        # Verify we got data (either from browser or mock)
        assert country_data is not None, "No data returned"
        assert 'news' in country_data, "No news in data"
        assert 'weather' in country_data, "No weather in data"
        assert len(country_data['news']) > 0, "No news articles"
        
        print(f"\n✅ Success!")
        print(f"   News articles: {len(country_data['news'])}")
        print(f"   Weather: {country_data['weather']['description']} {country_data['weather']['temp']}°C")
        print(f"   City: {country_data['weather']['city']}")
        
        print("\n" + "=" * 80)
        print("✅ TEST PASSED - Errors handled gracefully, data collected")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_browser_collectors()
    sys.exit(0 if success else 1)
