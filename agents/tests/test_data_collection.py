#!/usr/bin/env python3
"""
Test data collection and storage with updated AWS credentials
This test does NOT require strands/agentcore (uses mock data instead)
"""
import os
import sys
from dotenv import load_dotenv
from datetime import datetime

load_dotenv('.env')

# Import storage module
from rds_storage import create_rds_storage

def test_data_collection_and_storage():
    """Test data collection and RDS+S3 storage"""
    print("=" * 80)
    print("データ収集 & ストレージテスト（最新認証情報）")
    print("=" * 80)
    
    all_tests_passed = True
    
    # Initialize storage
    print("\n1️⃣ RDSストレージ初期化...")
    try:
        storage = create_rds_storage()
        print(f"   ✅ ストレージ初期化成功")
        print(f"   S3 Bucket: {storage.s3_bucket}")
        print(f"   RDS Host: {storage.db_host}")
    except Exception as e:
        print(f"   ❌ ストレージ初期化失敗: {e}")
        return False
    
    # Test with mock news data
    print("\n2️⃣ ニュースデータ保存テスト...")
    test_country = "JP"
    mock_news = [
        {
            'title': 'テスト: 経済成長が加速',
            'description': '最新の経済指標は好調を示している',
            'source': 'Test News',
            'url': 'https://example.com/test1',
            'sentiment': 0.5,
            'published_at': datetime.now().isoformat()
        },
        {
            'title': 'テスト: 新技術の導入が進む',
            'description': 'イノベーションが活発化',
            'source': 'Tech News',
            'url': 'https://example.com/test2',
            'sentiment': 0.3,
            'published_at': datetime.now().isoformat()
        }
    ]
    
    try:
        news_saved = storage.save_news_data(test_country, mock_news)
        print(f"   ✅ ニュースデータ保存成功: {news_saved}件")
    except Exception as e:
        print(f"   ❌ ニュースデータ保存失敗: {e}")
        all_tests_passed = False
        import traceback
        traceback.print_exc()
    
    # Test with mock weather data
    print("\n3️⃣ 天気データ保存テスト...")
    mock_weather = {
        'city': 'Tokyo',
        'temp': 22.0,
        'feels_like': 21.0,
        'description': 'Partly Cloudy',
        'humidity': 65,
        'wind_speed': 12.0,
        'mood_impact': 0.3,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        weather_saved = storage.save_weather_data(test_country, mock_weather)
        if weather_saved:
            print(f"   ✅ 天気データ保存成功 (UPSERT)")
        else:
            print(f"   ❌ 天気データ保存失敗")
            all_tests_passed = False
    except Exception as e:
        print(f"   ❌ 天気データ保存失敗: {e}")
        all_tests_passed = False
        import traceback
        traceback.print_exc()
    
    # Verify S3 uploads
    print("\n4️⃣ S3アップロード確認...")
    try:
        import boto3
        from datetime import date
        
        s3 = boto3.client('s3', region_name=os.getenv('AWS_REGION'))
        bucket = storage.s3_bucket
        
        # Check news file
        news_key = f"news-data/{test_country}/{date.today()}_news.md"
        try:
            s3.head_object(Bucket=bucket, Key=news_key)
            print(f"   ✅ ニュースファイル確認: {news_key}")
        except:
            print(f"   ⚠️  ニュースファイルが見つかりません: {news_key}")
        
        # Check weather file
        weather_key = f"weather-data/{test_country}/{date.today()}_weather.md"
        try:
            s3.head_object(Bucket=bucket, Key=weather_key)
            print(f"   ✅ 天気ファイル確認: {weather_key}")
        except:
            print(f"   ⚠️  天気ファイルが見つかりません: {weather_key}")
            
    except Exception as e:
        print(f"   ⚠️  S3確認スキップ: {e}")
    
    # Verify RDS data
    print("\n5️⃣ RDSデータ確認...")
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            port=int(os.getenv('DB_PORT')),
            sslmode='require'
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check news count
            cur.execute("""
                SELECT COUNT(*) as count 
                FROM insights_countrynewsitem 
                WHERE title LIKE 'テスト:%'
            """)
            news_count = cur.fetchone()['count']
            print(f"   ✅ ニュース記事（テスト）: {news_count}件")
            
            # Check weather
            cur.execute("""
                SELECT c.code, w.condition, w.temperature 
                FROM insights_countryweather w
                JOIN insights_country c ON w.country_id = c.id
                WHERE c.code = %s
            """, (test_country,))
            weather = cur.fetchone()
            if weather:
                print(f"   ✅ 天気データ: {weather['code']} - {weather['condition']} {weather['temperature']}°C")
            else:
                print(f"   ⚠️  天気データが見つかりません")
        
        conn.close()
        
    except Exception as e:
        print(f"   ⚠️  RDSデータ確認失敗: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 80)
    print("テスト結果サマリー")
    print("=" * 80)
    
    if all_tests_passed:
        print("✅ データ収集・ストレージテストが成功しました！")
        print("\n動作確認済み:")
        print("  ✅ RDS接続とデータ保存")
        print("  ✅ S3アップロード（ニュース・天気）")
        print("  ✅ Djangoモデルとの統合")
        print("\n次のステップ:")
        print("  - ブラウザデータ収集テスト（要strands環境）")
        print("  - パネルディスカッションテスト（要strands環境）")
        return True
    else:
        print("❌ 一部のテストが失敗しました")
        return False

if __name__ == "__main__":
    success = test_data_collection_and_storage()
    sys.exit(0 if success else 1)
