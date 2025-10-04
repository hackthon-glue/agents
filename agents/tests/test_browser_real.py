#!/usr/bin/env python3
"""
Test real browser data collection (no mock fallback)
"""
import os
from dotenv import load_dotenv

load_dotenv('.env')

from browser_collectors import BrowserDataCollectionService

print("=" * 80)
print("ブラウザデータ収集テスト（モックなし）")
print("=" * 80)

# Initialize service
service = BrowserDataCollectionService(region=os.getenv('AWS_REGION', 'us-west-2'))

# Test with JP
country_code = 'JP'
print(f"\nテスト対象国: {country_code}")

try:
    country_data = service.collect_country_data(
        country_code=country_code,
        max_news=2
    )
    
    print("\n✅ データ収集成功!")
    print(f"   ニュース記事: {len(country_data['news'])}件")
    print(f"   天気データ: {country_data['weather']['city']}, {country_data['weather']['temp']}°C")
    
    # Show sample news
    if country_data['news']:
        print("\nニュース記事サンプル:")
        for i, article in enumerate(country_data['news'][:2], 1):
            print(f"   {i}. {article['title']}")
            print(f"      センチメント: {article['sentiment']}")
    
    print("\n天気詳細:")
    print(f"   説明: {country_data['weather']['description']}")
    print(f"   湿度: {country_data['weather']['humidity']}%")
    print(f"   風速: {country_data['weather']['wind_speed']} km/h")
    print(f"   ムード影響: {country_data['weather']['mood_impact']}")
    
except Exception as e:
    print(f"\n❌ データ収集失敗: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
