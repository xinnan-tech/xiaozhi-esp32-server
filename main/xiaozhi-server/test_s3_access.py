#!/usr/bin/env python3
"""
Test S3 access and generate presigned URLs
"""
import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_s3_access():
    """Test S3 access with current credentials"""
    
    # Get credentials from environment
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    bucket_name = os.getenv('S3_BUCKET_NAME', 'cheeko-audio-files')
    
    print("=" * 60)
    print("S3 ACCESS TEST")
    print("=" * 60)
    print(f"AWS Region: {aws_region}")
    print(f"S3 Bucket: {bucket_name}")
    print(f"Access Key: {aws_access_key[:10]}..." if aws_access_key else "Access Key: NOT SET")
    print(f"Secret Key: {'*' * 10}..." if aws_secret_key else "Secret Key: NOT SET")
    print("-" * 60)
    
    if not aws_access_key or not aws_secret_key:
        print("❌ ERROR: AWS credentials not found in environment")
        return False
    
    try:
        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )
        
        # Test 1: List bucket contents (first 10 objects)
        print("🔍 Testing bucket access...")
        try:
            response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=10)
            if 'Contents' in response:
                print(f"✅ Bucket accessible! Found {len(response['Contents'])} objects")
                for obj in response['Contents'][:5]:  # Show first 5
                    print(f"   - {obj['Key']} ({obj['Size']} bytes)")
            else:
                print("⚠️  Bucket is empty or no access to contents")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            print(f"❌ Bucket access failed: {error_code} - {e.response['Error']['Message']}")
            return False
        
        # Test 2: Generate presigned URL for a test file
        print("\n🔗 Testing presigned URL generation...")
        test_key = "music/Hindi/Bum Bum Bole.mp3"  # The file from the error log
        
        try:
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': test_key},
                ExpiresIn=3600  # 1 hour
            )
            print(f"✅ Presigned URL generated successfully:")
            print(f"   {presigned_url}")
            
            # Test 3: Try to access the presigned URL
            print("\n🌐 Testing presigned URL access...")
            import requests
            try:
                response = requests.head(presigned_url, timeout=10)
                if response.status_code == 200:
                    print(f"✅ Presigned URL works! File size: {response.headers.get('content-length', 'unknown')} bytes")
                else:
                    print(f"❌ Presigned URL failed: HTTP {response.status_code}")
            except Exception as e:
                print(f"❌ Network error testing presigned URL: {e}")
                
        except ClientError as e:
            print(f"❌ Failed to generate presigned URL: {e}")
            return False
        
        # Test 4: Check bucket policy
        print("\n🔒 Checking bucket policy...")
        try:
            policy_response = s3_client.get_bucket_policy(Bucket=bucket_name)
            print("✅ Bucket policy exists")
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchBucketPolicy':
                print("⚠️  No bucket policy found - this might explain the 403 errors")
                print("💡 Consider adding a public read policy for the audio files")
            else:
                print(f"❌ Error checking bucket policy: {e}")
        
        print("\n" + "=" * 60)
        print("✅ S3 ACCESS TEST COMPLETED SUCCESSFULLY")
        print("💡 The system should work with presigned URLs")
        print("=" * 60)
        return True
        
    except NoCredentialsError:
        print("❌ ERROR: Invalid AWS credentials")
        return False
    except Exception as e:
        print(f"❌ ERROR: Unexpected error: {e}")
        return False

def test_cdn_helper():
    """Test CDN helper functionality"""
    print("\n" + "=" * 60)
    print("CDN HELPER TEST")
    print("=" * 60)
    
    try:
        from utils.cdn_helper import cdn, get_audio_url, is_cdn_ready
        
        # Test CDN status
        status = cdn.get_status()
        print("CDN Configuration:")
        for key, value in status.items():
            print(f"  {key}: {value}")
        
        print(f"\nCDN Ready: {'✅ YES' if is_cdn_ready() else '❌ NO'}")
        
        # Test URL generation
        test_file = "music/Hindi/Bum Bum Bole.mp3"
        cdn_url = get_audio_url(test_file)
        print(f"\nTest URL: {cdn_url}")
        
    except Exception as e:
        print(f"❌ CDN Helper error: {e}")

if __name__ == "__main__":
    test_s3_access()
    test_cdn_helper()