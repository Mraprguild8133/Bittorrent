import os
import boto3
import asyncio
import aiofiles
from botocore.exceptions import ClientError
from utils import hrb
import logging

logger = logging.getLogger(__name__)

class WasabiClient:
    def __init__(self):
        self.access_key = os.environ.get("WASABI_ACCESS_KEY")
        self.secret_key = os.environ.get("WASABI_SECRET_KEY")
        self.region = os.environ.get("WASABI_REGION", "us-east-1")
        self.bucket_name = os.environ.get("WASABI_BUCKET")
        self.endpoint_url = f"https://s3.{self.region}.wasabisys.com"
        
        if not all([self.access_key, self.secret_key, self.bucket_name]):
            raise ValueError("Wasabi credentials not configured properly")
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            endpoint_url=self.endpoint_url,
            region_name=self.region
        )
    
    async def upload_file(self, file_path, object_name=None):
        """Upload a file to Wasabi bucket"""
        try:
            if object_name is None:
                object_name = os.path.basename(file_path)
            
            # Upload the file
            self.s3_client.upload_file(file_path, self.bucket_name, object_name)
            
            # Generate presigned URL (valid for 7 days)
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_name},
                ExpiresIn=604800  # 7 days
            )
            
            logger.info(f"File uploaded successfully: {object_name}")
            return {
                'success': True,
                'url': url,
                'object_name': object_name,
                'bucket': self.bucket_name
            }
            
        except ClientError as e:
            logger.error(f"Wasabi upload error: {str(e)}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"Unexpected error during upload: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def download_file(self, object_name, file_path):
        """Download a file from Wasabi bucket"""
        try:
            self.s3_client.download_file(self.bucket_name, object_name, file_path)
            logger.info(f"File downloaded successfully: {object_name}")
            return {'success': True, 'file_path': file_path}
        except ClientError as e:
            logger.error(f"Wasabi download error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def delete_file(self, object_name):
        """Delete a file from Wasabi bucket"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_name)
            logger.info(f"File deleted successfully: {object_name}")
            return {'success': True}
        except ClientError as e:
            logger.error(f"Wasabi delete error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def list_files(self, prefix=""):
        """List files in Wasabi bucket"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': hrb(obj['Size']),
                        'last_modified': obj['LastModified']
                    })
            return {'success': True, 'files': files}
        except ClientError as e:
            logger.error(f"Wasabi list error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_file_info(self, object_name):
        """Get information about a file"""
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_name
            )
            return {
                'success': True,
                'size': response['ContentLength'],
                'content_type': response['ContentType'],
                'last_modified': response['LastModified']
            }
        except ClientError as e:
            logger.error(f"Wasabi file info error: {str(e)}")
            return {'success': False, 'error': str(e)}

# Global Wasabi client instance
wasabi_client = WasabiClient()
