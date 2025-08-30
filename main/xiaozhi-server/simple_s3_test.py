#!/usr/bin/env python3
"""
Simple S3 access test without Unicode characters
"""
import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_s3_simple():
    """Simple S3 test"""
    
    # Get credentials
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    bucket_name = os.getenv('S3_BUCKET_NAME', 'cheeko-audio-files')
    
    print("S3 ACCESS TEST")
    print("Region:", aws_region)
    print("Bucket:", bucket_name)
    print("Access Key:", aws_access_key[:10] + "..." if aws_access_key else "NOT SET")
    
    if not aws_access_key or not aws_secret_key:
        print("ERROR: AWS credentials not found")
        return False
    
    try:
        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )
        
        # Test bucket access
        print("Testing bucket access...")
        response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
        
        if 'Contents' in response:
            print("SUCCESS: Bucket accessible!")
            for obj in response['Contents']:
                print(f"  File: {obj['Key']} ({obj['Size']} bytes)")
        else:
            print("WARNING: Bucket is empty")
        
        # Test presigned URL
        print("Testing presigned URL...")
        test_key = "music/Hindi/Bum Bum Bole.mp3"
        
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': test_key},
            ExpiresIn=3600
        )
        print("SUCCESS: Presigned URL generated")
        print("URL:", presigned_url[:100] + "...")
        
        # Test URL access
        import requests
        response = requests.head(presigned_url, timeout=10)
        print(f"URL Test: HTTP {response.status_code}")
        
        if response.status_code == 200:
            print("SUCCESS: File is accessible via presigned URL")
            return True
        elif response.status_code == 403:
            print("ERROR: 403 Forbidden - Check bucket permissions")
            return False
        else:
            print(f"ERROR: HTTP {response.status_code}")
            return False
            
    except ClientError as e:
        print(f"AWS Error: {e.response['Error']['Code']} - {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_s3_simple()