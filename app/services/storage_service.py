import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from app.core.config import settings
from typing import BinaryIO
import logging

logger = logging.getLogger(__name__)

# Boto3 will automatically use the IAM role credentials from the EC2 instance metadata
s3_client = boto3.client(
    's3',
    region_name=settings.AWS_REGION,
    # No need to specify keys if using an IAM role on EC2
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
)

BUCKET_NAME: str = settings.S3_BUCKET_NAME

def create_s3_bucket_if_not_exists() -> None:
    """
    Ensure the S3 bucket exists. Create it if it does not exist.
    """
    try:
        s3_client.head_bucket(Bucket=BUCKET_NAME)
        logger.info(f"Bucket '{BUCKET_NAME}' already exists.")
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            logger.info(f"Bucket '{BUCKET_NAME}' not found. Creating it.")
            # For regions other than us-east-1, you must specify a LocationConstraint
            if settings.AWS_REGION != 'us-east-1':
                s3_client.create_bucket(
                    Bucket=BUCKET_NAME,
                    CreateBucketConfiguration={'LocationConstraint': settings.AWS_REGION}
                )
            else:
                 s3_client.create_bucket(Bucket=BUCKET_NAME)
            logger.info(f"Bucket '{BUCKET_NAME}' created.")
        else:
            logger.error(f"Error checking for bucket: {e}", exc_info=True)
            raise

def upload_file_obj(file_obj: BinaryIO, object_name: str) -> bool:
    """
    Upload a file-like object to the S3 bucket.
    """
    try:
        s3_client.upload_fileobj(file_obj, BUCKET_NAME, object_name)
    except ClientError as e:
        logger.error(f"Error uploading to S3: {e}", exc_info=True)
        return False
    return True

def download_file(object_name: str, file_path: str) -> bool:
    """
    Download an object from the S3 bucket to a local file.
    """
    try:
        s3_client.download_file(BUCKET_NAME, object_name, file_path)
    except ClientError as e:
        logger.error(f"Error downloading from S3: {e}", exc_info=True)
        return False
    return True

def delete_file(object_name: str) -> bool:
    """
    Delete an object from the S3 bucket.
    """
    try:
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=object_name)
    except ClientError as e:
        logger.error(f"Error deleting from S3: {e}", exc_info=True)
        return False
    return True
