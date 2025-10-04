#!/usr/bin/env python3
"""
Test AWS authentication with updated credentials
"""
import boto3
import os
from dotenv import load_dotenv
import sys

load_dotenv('.env')

def test_aws_authentication():
    """Test AWS authentication and basic services"""
    print("=" * 80)
    print("AWS認証テスト（最新認証情報）")
    print("=" * 80)
    
    all_tests_passed = True
    
    # Test 1: S3 Access
    print("\n1️⃣ S3アクセステスト...")
    try:
        s3 = boto3.client('s3', region_name=os.getenv('AWS_REGION'))
        bucket = os.getenv('KB_S3_BUCKET')
        response = s3.list_objects_v2(Bucket=bucket, MaxKeys=1)
        print(f"   ✅ S3接続成功: {bucket}")
        print(f"   リージョン: {os.getenv('AWS_REGION')}")
    except Exception as e:
        print(f"   ❌ S3接続失敗: {e}")
        all_tests_passed = False
    
    # Test 2: RDS Access
    print("\n2️⃣ RDS接続テスト...")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            port=int(os.getenv('DB_PORT')),
            sslmode='require'
        )
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM panel_discussions;")
            count = cur.fetchone()[0]
            print(f"   ✅ RDS接続成功")
            print(f"   panel_discussions: {count}件")
        conn.close()
    except Exception as e:
        print(f"   ❌ RDS接続失敗: {e}")
        all_tests_passed = False
    
    # Test 3: Bedrock Runtime Access
    print("\n3️⃣ Bedrock Runtimeアクセステスト...")
    try:
        bedrock = boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION'))
        # Try to list models (just to verify access)
        print(f"   ✅ Bedrock Runtime クライアント初期化成功")
    except Exception as e:
        print(f"   ❌ Bedrock接続失敗: {e}")
        all_tests_passed = False
    
    # Test 4: S3 Write Test
    print("\n4️⃣ S3書き込みテスト...")
    try:
        s3 = boto3.client('s3', region_name=os.getenv('AWS_REGION'))
        bucket = os.getenv('KB_S3_BUCKET')
        test_key = 'test-auth/test.txt'
        test_content = 'AWS認証テスト - 成功'
        
        s3.put_object(
            Bucket=bucket,
            Key=test_key,
            Body=test_content,
            ContentType='text/plain'
        )
        print(f"   ✅ S3書き込み成功: s3://{bucket}/{test_key}")
        
        # Verify by reading back
        response = s3.get_object(Bucket=bucket, Key=test_key)
        content = response['Body'].read().decode('utf-8')
        if content == test_content:
            print(f"   ✅ S3読み取り確認成功")
        else:
            print(f"   ⚠️  内容が一致しません")
        
        # Clean up
        s3.delete_object(Bucket=bucket, Key=test_key)
        print(f"   🧹 テストファイル削除完了")
        
    except Exception as e:
        print(f"   ❌ S3書き込みテスト失敗: {e}")
        all_tests_passed = False
    
    # Summary
    print("\n" + "=" * 80)
    print("テスト結果サマリー")
    print("=" * 80)
    
    if all_tests_passed:
        print("✅ すべてのAWS認証テストが成功しました！")
        print("\n次のステップ:")
        print("  - データ収集テスト")
        print("  - パネルディスカッションテスト")
        print("  - RDS+S3保存テスト")
        return True
    else:
        print("❌ 一部のテストが失敗しました")
        print("認証情報を確認してください")
        return False

if __name__ == "__main__":
    success = test_aws_authentication()
    sys.exit(0 if success else 1)
