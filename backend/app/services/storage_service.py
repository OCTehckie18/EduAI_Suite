"""
Storage Service for Slido
Handles file uploads to S3-compatible storage (AWS S3 or MinIO)
"""
import os
import boto3
from botocore.exceptions import ClientError
from datetime import timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing file uploads to S3-compatible storage"""

    def __init__(self):
        # Configuration from environment variables
        self.use_s3 = os.getenv('USE_S3', 'false').lower() == 'true'
        self.bucket_name = os.getenv('S3_BUCKET_NAME', 'edui-presentations')
        self.region = os.getenv('S3_REGION', 'us-east-1')

        if self.use_s3:
            # AWS S3 Configuration
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=self.region
            )
            self.endpoint_url = None
        else:
            # MinIO Configuration (Local Development)
            self.endpoint_url = os.getenv(
                'MINIO_ENDPOINT', 'http://localhost:9000')
            self.s3_client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=os.getenv('MINIO_ROOT_USER', 'minioadmin'),
                aws_secret_access_key=os.getenv(
                    'MINIO_ROOT_PASSWORD', 'minioadmin'),
                region_name=self.region,
                use_ssl=self.endpoint_url.startswith('https')
            )

        self.offline_mode = False
        self.local_storage_path = os.path.join(os.getcwd(), 'local_uploads')
        if not os.path.exists(self.local_storage_path):
            os.makedirs(self.local_storage_path, exist_ok=True)

        try:
            self._ensure_bucket_exists()
        except Exception as e:
            logger.warning(f"Could not connect to storage provider: {e}. Falling back to local offline mode.")
            self.offline_mode = True

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket '{self.bucket_name}' exists")
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Created bucket '{self.bucket_name}'")
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
            else:
                logger.error(f"Error checking bucket: {e}")

    def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        folder: str = 'presentations',
        content_type: str = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    ) -> Optional[str]:
        """
        Upload file to S3-compatible storage

        Args:
            file_content: File bytes
            file_name: Name of file (unique identifier recommended)
            folder: Storage folder (default: presentations)
            content_type: MIME type of file

        Returns:
            S3 object key (path) or None if upload fails
        """
        try:
            object_key = f"{folder}/{file_name}"

            if self.offline_mode:
                local_path = os.path.join(self.local_storage_path, object_key.replace('/', '_'))
                with open(local_path, 'wb') as f:
                    f.write(file_content)
                logger.info(f"Offline mode: Saved file locally to {local_path}")
                return object_key

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=file_content,
                ContentType=content_type,
                ServerSideEncryption='AES256' if self.use_s3 else None
            )

            logger.info(f"Uploaded file to {object_key}")
            return object_key
        except ClientError as e:
            logger.error(f"Failed to upload file: {e}")
            return None

    def generate_presigned_url(
        self,
        object_key: str,
        expiration: int = 3600,  # 1 hour default
        operation: str = 'get_object'
    ) -> Optional[str]:
        """
        Generate presigned URL for accessing object

        Args:
            object_key: S3 object key (path)
            expiration: URL expiration time in seconds
            operation: S3 operation (get_object, put_object, etc.)

        Returns:
            Presigned URL or None if generation fails
        """
        try:
            if self.offline_mode:
                return f"/local_uploads/{object_key.replace('/', '_')}"

            url = self.s3_client.generate_presigned_url(
                operation,
                Params={'Bucket': self.bucket_name, 'Key': object_key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None

    def delete_file(self, object_key: str) -> bool:
        """
        Delete file from S3 storage

        Args:
            object_key: S3 object key (path)

        Returns:
            True if deletion successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name, Key=object_key)
            logger.info(f"Deleted file: {object_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete file: {e}")
            return False

    def get_file(self, object_key: str) -> Optional[bytes]:
        """
        Download file from S3 storage

        Args:
            object_key: S3 object key (path)

        Returns:
            File bytes or None if download fails
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name, Key=object_key)
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"Failed to download file: {e}")
            return None

    def list_files(self, folder: str = 'presentations', max_keys: int = 100) -> list:
        """
        List files in a folder

        Args:
            folder: Folder path
            max_keys: Maximum number of keys to return

        Returns:
            List of file objects with metadata
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=f"{folder}/",
                MaxKeys=max_keys
            )

            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'storage_class': obj['StorageClass']
                    })

            return files
        except ClientError as e:
            logger.error(f"Failed to list files: {e}")
            return []

    def get_file_url(self, object_key: str, temporary: bool = True, expiration: int = 3600) -> Optional[str]:
        """
        Get URL for accessing file

        Args:
            object_key: S3 object key (path)
            temporary: Use presigned URL (temporary access) if True, else public URL
            expiration: URL expiration time in seconds (for presigned URLs)

        Returns:
            File URL or None if generation fails
        """
        if temporary:
            return self.generate_presigned_url(object_key, expiration)
        else:
            # Public URL (if bucket is public or CloudFront is configured)
            if self.endpoint_url:  # MinIO
                return f"{self.endpoint_url}/{self.bucket_name}/{object_key}"
            else:  # AWS S3
                return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{object_key}"


# Global storage service instance
storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get or initialize storage service"""
    global storage_service
    if storage_service is None:
        if os.getenv("STORAGE_PROVIDER", "local").lower() == "supabase":
            from app.services.supabase_storage_service import SupabaseStorageService
            storage_service = SupabaseStorageService()
        else:
            storage_service = StorageService()
    return storage_service
