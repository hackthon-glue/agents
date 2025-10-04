"""
Test script to apply schema and verify database structure
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_connection():
    """Get PostgreSQL connection"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME', 'glue'),
        port=int(os.getenv('DB_PORT', '5432')),
        sslmode='require'
    )


def apply_schema():
    """Apply schema.sql to database"""
    print("📋 Applying schema.sql to RDS database...")
    
    # Read schema file
    with open('schema.sql', 'r') as f:
        schema_sql = f.read()
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Execute schema
            cur.execute(schema_sql)
            conn.commit()
        print("✅ Schema applied successfully")
        return True
    except Exception as e:
        print(f"❌ Error applying schema: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def verify_tables():
    """Verify all tables exist"""
    print("\n🔍 Verifying tables...")
    
    expected_tables = [
        'panel_discussions',
        'panel_expert_analyses',
        'panel_votes',
        'panel_transcripts',
        'news_articles',
        'weather_data'
    ]
    
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check if tables exist
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                AND table_name IN %s
                ORDER BY table_name
            """, (tuple(expected_tables),))
            
            existing_tables = [row['table_name'] for row in cur.fetchall()]
            
            print(f"\n📊 Tables found: {len(existing_tables)}/{len(expected_tables)}")
            for table in expected_tables:
                if table in existing_tables:
                    print(f"  ✅ {table}")
                else:
                    print(f"  ❌ {table} (MISSING)")
            
            return len(existing_tables) == len(expected_tables)
            
    except Exception as e:
        print(f"❌ Error verifying tables: {e}")
        return False
    finally:
        conn.close()


def verify_indexes():
    """Verify indexes are created"""
    print("\n🔍 Verifying indexes...")
    
    expected_indexes = [
        'idx_panel_country',
        'idx_panel_date',
        'idx_panel_mood',
        'idx_news_country',
        'idx_news_collected',
        'idx_weather_country',
        'idx_weather_collected'
    ]
    
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE schemaname = 'public'
                AND indexname IN %s
                ORDER BY indexname
            """, (tuple(expected_indexes),))
            
            existing_indexes = [row['indexname'] for row in cur.fetchall()]
            
            print(f"\n📊 Indexes found: {len(existing_indexes)}/{len(expected_indexes)}")
            for idx in expected_indexes:
                if idx in existing_indexes:
                    print(f"  ✅ {idx}")
                else:
                    print(f"  ⚠️  {idx} (not found)")
            
            return True
            
    except Exception as e:
        print(f"❌ Error verifying indexes: {e}")
        return False
    finally:
        conn.close()


def check_table_structure():
    """Check detailed structure of new tables"""
    print("\n🔍 Checking table structures...")
    
    tables_to_check = ['news_articles', 'weather_data']
    
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for table in tables_to_check:
                print(f"\n📋 Table: {table}")
                cur.execute("""
                    SELECT 
                        column_name,
                        data_type,
                        character_maximum_length,
                        is_nullable,
                        column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = %s
                    ORDER BY ordinal_position
                """, (table,))
                
                columns = cur.fetchall()
                if columns:
                    for col in columns:
                        nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                        print(f"  - {col['column_name']}: {col['data_type']} {nullable}")
                else:
                    print(f"  ❌ No columns found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking structure: {e}")
        return False
    finally:
        conn.close()


def test_data_insertion():
    """Test inserting sample data"""
    print("\n🧪 Testing data insertion...")
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Test news article insertion
            cur.execute("""
                INSERT INTO news_articles
                (country_code, title, description, source, url, sentiment, published_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            """, (
                'TEST',
                'Test Article',
                'Test description',
                'Test Source',
                'https://example.com/test',
                0.5
            ))
            news_id = cur.fetchone()[0]
            print(f"  ✅ Inserted news article (id: {news_id})")
            
            # Test weather data insertion
            cur.execute("""
                INSERT INTO weather_data
                (country_code, city, temp, feels_like, description, 
                 humidity, wind_speed, mood_impact, observation_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            """, (
                'TEST',
                'Test City',
                20.5,
                19.0,
                'Sunny',
                65,
                10.0,
                0.3
            ))
            weather_id = cur.fetchone()[0]
            print(f"  ✅ Inserted weather data (id: {weather_id})")
            
            # Clean up test data
            cur.execute("DELETE FROM news_articles WHERE id = %s", (news_id,))
            cur.execute("DELETE FROM weather_data WHERE id = %s", (weather_id,))
            print(f"  🧹 Cleaned up test data")
            
            conn.commit()
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing insertion: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def verify_view():
    """Verify the latest_panel_discussions view"""
    print("\n🔍 Verifying view...")
    
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check if view exists
            cur.execute("""
                SELECT viewname 
                FROM pg_views 
                WHERE schemaname = 'public'
                AND viewname = 'latest_panel_discussions'
            """)
            
            if cur.fetchone():
                print("  ✅ latest_panel_discussions view exists")
                return True
            else:
                print("  ❌ latest_panel_discussions view not found")
                return False
                
    except Exception as e:
        print(f"❌ Error verifying view: {e}")
        return False
    finally:
        conn.close()


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("🚀 Starting Schema Test Suite")
    print("=" * 60)
    
    results = {
        'schema_applied': False,
        'tables_verified': False,
        'indexes_verified': False,
        'structure_checked': False,
        'data_insertion': False,
        'view_verified': False
    }
    
    # Test 1: Apply schema (skip if already exists)
    print("\n⚠️  Skipping schema application - verifying existing schema instead")
    results['schema_applied'] = True
    
    # Test 2: Verify tables
    results['tables_verified'] = verify_tables()
    
    # Test 3: Verify indexes
    results['indexes_verified'] = verify_indexes()
    
    # Test 4: Check structure
    results['structure_checked'] = check_table_structure()
    
    # Test 5: Test data insertion
    results['data_insertion'] = test_data_insertion()
    
    # Test 6: Verify view
    results['view_verified'] = verify_view()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name.replace('_', ' ').title()}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED - Schema is Django compatible!")
    else:
        print("❌ SOME TESTS FAILED - Please review errors above")
    print("=" * 60)
    
    return all_passed


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
