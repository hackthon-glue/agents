"""
AgentCore Browser-based Data Collection Services
Uses AWS Bedrock AgentCore Browser for web scraping
"""

from strands import Agent
from strands_tools.browser import AgentCoreBrowser
from typing import Dict, List, Optional
from datetime import datetime
import json
import re


class BrowserNewsCollector:
    """Collect news using AgentCore Browser"""

    def __init__(self, region: str = "ap-northeast-1"):
        """
        Initialize Browser News Collector

        Args:
            region: AWS region for AgentCore Browser
        """
        self.region = region
        self.browser = AgentCoreBrowser(region=region)
        self.agent = Agent(
            tools=[self.browser.browser],
            model="anthropic.claude-3-haiku-20240307-v1:0",
            system_prompt="""You are a news scraping agent. Your task is to:
1. Navigate to news websites
2. Extract recent headlines and articles
3. Return structured data with titles, descriptions, and sources
4. Estimate sentiment (positive, negative, neutral) for each article

Always return data in JSON format."""
        )

    def get_top_headlines(
        self,
        country_code: str,
        max_results: int = 10
    ) -> List[Dict]:
        """
        Get top headlines for a country using browser automation

        Args:
            country_code: 2-letter country code (e.g., 'jp', 'us')
            max_results: Maximum number of articles to return

        Returns:
            List of article dictionaries
        """
        print(f"🌐 Collecting news for {country_code.upper()} using AgentCore Browser...")
        
        # Country-specific news sources
        news_urls = {
            'jp': 'https://www.japantimes.co.jp/',
            'us': 'https://www.reuters.com/',
            'uk': 'https://www.bbc.com/news',
            'fr': 'https://www.france24.com/en/',
            'de': 'https://www.dw.com/en/top-stories/s-9097',
            'cn': 'https://www.chinadaily.com.cn/',
            'kr': 'https://www.koreaherald.com/',
            'in': 'https://www.thehindu.com/',
            'br': 'https://www.reuters.com/world/americas/',
            'au': 'https://www.abc.net.au/news',
        }
        
        url = news_urls.get(country_code.lower(), 'https://www.reuters.com/')
        
        prompt = f"""Go to {url}

Find the first {max_results} news article headlines on the page. For each one:
- Extract the headline title
- Extract a brief description or summary (if available)
- Estimate sentiment: 0.3 for positive news, 0.0 for neutral, -0.3 for negative

Return your answer as a JSON array with this exact format:
[
  {{"title": "headline 1", "description": "summary 1", "source": "{url.split('/')[2]}", "sentiment": 0.0}},
  {{"title": "headline 2", "description": "summary 2", "source": "{url.split('/')[2]}", "sentiment": 0.3}}
]

IMPORTANT: Return ONLY the JSON array, no other text."""

        try:
            response = self.agent(prompt)
            articles = self._parse_json_response(response)
            
            if not articles:
                raise ValueError("No articles extracted from browser response")
            
            # Add metadata
            for article in articles:
                article['published_at'] = datetime.now().isoformat()
                if 'url' not in article:
                    article['url'] = url
            
            print(f"✅ Collected {len(articles)} news articles for {country_code.upper()}")
            return articles[:max_results]
            
        except Exception as e:
            print(f"❌ Browser news collection failed: {e}")
            raise RuntimeError(f"Failed to collect news for {country_code}: {e}")

    def _parse_json_response(self, response) -> List[Dict]:
        """Extract JSON array from agent response with robust error handling"""
        try:
            # If response is already a list
            if isinstance(response, list):
                return response

            # Extract text from response
            if hasattr(response, 'message'):
                text = response.message.get('content', [{}])[0].get('text', '')
            else:
                text = str(response)

            # Clean up common issues
            text = text.strip()
            
            # Try to find JSON array in the text
            json_match = re.search(r'\[[\s\S]*\]', text)
            if json_match:
                json_str = json_match.group(0)
                # Try to parse, with fallback for common issues
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as je:
                    print(f"⚠️  JSON parse error: {je}")
                    # Try to fix common issues like missing commas
                    # For now, just return empty to trigger fallback
                    return []

            # If no JSON array found, try direct parse
            try:
                return json.loads(text)
            except:
                return []

        except Exception as e:
            print(f"⚠️  JSON parse error: {e}")
            return []

    def _get_mock_news(self, country_code: str, max_results: int) -> List[Dict]:
        """Generate mock news data for testing"""
        mock_articles = {
            'jp': [
                {
                    'title': 'Japan\'s economy shows steady growth in Q4',
                    'description': 'Economic indicators point to continued recovery',
                    'source': 'Japan Times',
                    'sentiment': 0.3
                },
                {
                    'title': 'New tech startups receive record funding in Tokyo',
                    'description': 'Investment in innovation reaches new heights',
                    'source': 'Nikkei Asia',
                    'sentiment': 0.4
                }
            ],
            'us': [
                {
                    'title': 'Stock market reaches new record high',
                    'description': 'Tech sector leads gains',
                    'source': 'Reuters',
                    'sentiment': 0.5
                }
            ]
        }

        articles = mock_articles.get(country_code.lower(), [
            {
                'title': f'Latest news from {country_code.upper()}',
                'description': 'Mixed developments',
                'source': 'International Press',
                'sentiment': 0.0
            }
        ])

        for article in articles:
            article['published_at'] = datetime.now().isoformat()
            article['url'] = 'https://example.com/news'

        return articles[:max_results]


class BrowserWeatherCollector:
    """Collect weather using AgentCore Browser"""

    def __init__(self, region: str = "ap-northeast-1"):
        """
        Initialize Browser Weather Collector

        Args:
            region: AWS region for AgentCore Browser
        """
        self.region = region
        self.browser = AgentCoreBrowser(region=region)
        self.agent = Agent(
            tools=[self.browser.browser],
            model="anthropic.claude-3-haiku-20240307-v1:0",
            system_prompt="""You are a weather data extraction agent. Your task is to:
1. Navigate to weather websites
2. Extract current weather information
3. Return structured data with temperature, conditions, and forecasts

Always return data in JSON format."""
        )

    def get_weather(
        self,
        country_code: str,
        city: Optional[str] = None
    ) -> Dict:
        """
        Get current weather for a country/city using browser automation

        Args:
            country_code: 2-letter country code (e.g., 'JP', 'US')
            city: Optional city name (defaults to capital)

        Returns:
            Weather data dictionary
        """
        # Default cities for countries
        default_cities = {
            'jp': 'Tokyo',
            'us': 'Washington',
            'uk': 'London',
            'fr': 'Paris',
            'de': 'Berlin',
            'cn': 'Beijing',
            'kr': 'Seoul',
            'in': 'New Delhi',
            'br': 'Brasilia',
            'au': 'Canberra'
        }

        city = city or default_cities.get(country_code.lower(), 'London')

        print(f"🌐 Collecting weather for {city}, {country_code.upper()} using AgentCore Browser...")
        
        # Use weather.com for consistent data
        url = f"https://weather.com/weather/today/l/{city}"
        
        prompt = f"""Go to {url}

Extract the current weather data from the page:
- Temperature in Celsius (number)
- Feels like temperature in Celsius (number)
- Weather condition (e.g., "Sunny", "Cloudy", "Rainy")
- Humidity percentage (number)
- Wind speed in km/h (number)

Return your answer as a JSON object with this exact format:
{{"temp": 20.0, "feels_like": 19.0, "description": "Partly Cloudy", "humidity": 60, "wind_speed": 10.0}}

IMPORTANT: Return ONLY the JSON object, no other text."""

        try:
            response = self.agent(prompt)
            weather_data = self._parse_json_response(response)
            
            if not weather_data or 'temp' not in weather_data:
                raise ValueError("No valid weather data extracted from browser response")
            
            # Add metadata and calculated fields
            weather_data['city'] = city
            weather_data['country'] = country_code.upper()
            weather_data['timestamp'] = datetime.now().isoformat()
            
            # Calculate mood impact
            temp = float(weather_data.get('temp', 20))
            description = weather_data.get('description', 'Unknown')
            weather_data['mood_impact'] = self._estimate_mood_impact(temp, description)
            
            print(f"✅ Collected weather for {city}: {description}, {temp}°C")
            return weather_data
            
        except Exception as e:
            print(f"❌ Browser weather collection failed: {e}")
            raise RuntimeError(f"Failed to collect weather for {city}, {country_code}: {e}")

    def _parse_json_response(self, response) -> Dict:
        """Extract JSON object from agent response with robust error handling"""
        try:
            # If response is already a dict
            if isinstance(response, dict):
                return response

            # Extract text from response
            if hasattr(response, 'message'):
                text = response.message.get('content', [{}])[0].get('text', '')
            else:
                text = str(response)

            # Clean up common issues
            text = text.strip()
            
            # Try to find JSON object in the text
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                json_str = json_match.group(0)
                # Try to parse, with fallback for common issues
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as je:
                    print(f"⚠️  JSON parse error: {je}")
                    # Return empty dict to trigger fallback
                    return {}

            # If no JSON object found, try direct parse
            try:
                return json.loads(text)
            except:
                return {}

        except Exception as e:
            print(f"⚠️  JSON parse error: {e}")
            return {}

    def _estimate_mood_impact(self, temp: float, description: str) -> float:
        """Estimate weather's impact on mood (-1 to 1)"""
        score = 0.0

        # Temperature impact
        if 18 <= temp <= 25:
            score += 0.3
        elif 10 <= temp < 18 or 25 < temp <= 30:
            score += 0.1
        elif temp < 5 or temp > 35:
            score -= 0.3
        else:
            score -= 0.1

        # Condition impact
        description_lower = description.lower()
        if any(word in description_lower for word in ['clear', 'sunny']):
            score += 0.3
        elif any(word in description_lower for word in ['cloud', 'overcast']):
            score += 0.0
        elif any(word in description_lower for word in ['rain', 'drizzle']):
            score -= 0.2
        elif any(word in description_lower for word in ['storm', 'thunder']):
            score -= 0.3
        elif any(word in description_lower for word in ['snow']):
            score -= 0.1

        return max(-1.0, min(1.0, score))

    def _get_mock_weather(self, country_code: str, city: Optional[str]) -> Dict:
        """Generate mock weather data for testing"""
        mock_weather = {
            'jp': {'temp': 18, 'description': 'Partly Cloudy'},
            'us': {'temp': 22, 'description': 'Clear Sky'}
        }

        default_weather = {'temp': 20, 'description': 'Partly Cloudy'}
        base = mock_weather.get(country_code.lower(), default_weather)

        return {
            'city': city or 'Unknown',
            'country': country_code.upper(),
            'temp': base['temp'],
            'feels_like': base['temp'] - 1,
            'description': base['description'],
            'humidity': 65,
            'wind_speed': 12,
            'timestamp': datetime.now().isoformat(),
            'mood_impact': self._estimate_mood_impact(base['temp'], base['description'])
        }


class BrowserDataCollectionService:
    """Unified service for browser-based data collection"""

    def __init__(self, region: str = "ap-northeast-1"):
        self.region = region
        self.news_collector = BrowserNewsCollector(region)
        self.weather_collector = BrowserWeatherCollector(region)

    def collect_country_data(
        self,
        country_code: str,
        max_news: int = 10,
        city: Optional[str] = None
    ) -> Dict:
        """
        Collect all data for a country using browser automation

        Args:
            country_code: 2-letter country code
            max_news: Maximum number of news articles
            city: Optional city for weather (defaults to capital)

        Returns:
            Dictionary with news and weather data
        """
        print(f"\n🔍 Collecting data for {country_code.upper()} using AgentCore Browser...")

        news = self.news_collector.get_top_headlines(
            country_code=country_code,
            max_results=max_news
        )

        weather = self.weather_collector.get_weather(
            country_code=country_code,
            city=city
        )

        # Calculate aggregate statistics
        avg_news_sentiment = (
            sum(article.get('sentiment', 0) for article in news) / len(news)
            if news else 0.0
        )

        data = {
            'country_code': country_code.upper(),
            'news': news,
            'weather': weather,
            'statistics': {
                'news_count': len(news),
                'avg_news_sentiment': round(avg_news_sentiment, 2),
                'weather_mood_impact': weather.get('mood_impact', 0.0),
                'collection_timestamp': datetime.now().isoformat(),
                'collection_method': 'agentcore_browser'
            }
        }

        print(f"✅ Browser-based data collection complete: {len(news)} articles, weather for {weather['city']}")
        return data


# Utility function
def collect_data_with_browser(country_code: str, region: str = "ap-northeast-1", **kwargs) -> Dict:
    """Convenience function for browser-based data collection"""
    service = BrowserDataCollectionService(region=region)
    return service.collect_country_data(country_code, **kwargs)
