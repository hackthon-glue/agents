#!/usr/bin/env python3
"""
Test script for CountrySentiment insertion
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from panel_discussion_strands_v2 import create_panel_discussion_strands_v2
from rds_storage import RDSPanelStorage

def main():
    print("=" * 60)
    print("TEST: CountrySentiment Insertion")
    print("=" * 60)
    
    # Test configuration
    test_country = "JP"
    test_topic = "Testing CountrySentiment insertion for Japan"
    
    # Initialize panel
    print("\n1️⃣ Initializing panel system...")
    panel = create_panel_discussion_strands_v2(
        model_id="anthropic.claude-3-haiku-20240307-v1:0"
    )
    print("✅ Panel initialized\n")
    
    # Initialize RDS storage
    print("2️⃣ Initializing RDS storage...")
    storage = RDSPanelStorage(
        db_host=os.getenv('DB_HOST'),
        db_user=os.getenv('DB_USER'),
        db_password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME', 'glue'),
        db_port=int(os.getenv('DB_PORT', '5432')),
        s3_bucket=os.getenv('KB_S3_BUCKET', 'team-for-glue-knowledge'),
        region=os.getenv('AWS_REGION', 'us-west-2')
    )
    print("✅ Storage initialized\n")
    
    # Test data
    test_data = {
        'news': [
            {'title': 'Test news item 1', 'summary': 'Test summary'},
            {'title': 'Test news item 2', 'summary': 'Another test'},
        ],
        'weather': {
            'description': 'Sunny',
            'temp': 25
        }
    }
    
    # Run discussion
    print("3️⃣ Running panel discussion...")
    result = panel.start_discussion(
        country_code=test_country,
        topic=test_topic,
        country_data=test_data,
        max_rounds=2  # Short test
    )
    print("✅ Discussion completed\n")
    
    # Save to RDS (including CountrySentiment)
    print("4️⃣ Saving to RDS (including CountrySentiment)...")
    discussion_id = storage.save_panel_result(result, test_country, skip_s3=True)
    print(f"✅ Saved to RDS with ID: {discussion_id}\n")
    
    # Verify CountrySentiment was saved
    print("5️⃣ Verifying CountrySentiment insertion...")
    import psycopg2
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME', 'glue'),
        port=int(os.getenv('DB_PORT', '5432')),
        sslmode='require'
    )
    
    try:
        with conn.cursor() as cur:
            # Check if CountrySentiment was inserted
            cur.execute("""
                SELECT cs.id, cs.country_id, cs.label, cs.score, cs.recorded_date, c.code
                FROM insights_countrysentiment cs
                JOIN insights_country c ON cs.country_id = c.id
                WHERE c.code = %s
                ORDER BY cs.id DESC
                LIMIT 1
            """, (test_country,))
            
            sentiment = cur.fetchone()
            if sentiment:
                print(f"✅ CountrySentiment found:")
                print(f"   ID: {sentiment[0]}")
                print(f"   Country ID: {sentiment[1]}")
                print(f"   Label: {sentiment[2]}")
                print(f"   Score: {sentiment[3]}")
                print(f"   Date: {sentiment[4]}")
                print(f"   Country Code: {sentiment[5]}")
            else:
                print(f"❌ No CountrySentiment found for {test_country}")
    finally:
        conn.close()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main()
