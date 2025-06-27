import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from app.core.config import settings

s3_client = boto3.client(
    's3',
    endpoint_url=settings.MINIO_SERVER_URL,
    aws_access_key_id=settings.MINIO_ACCESS_KEY,
    aws_secret_access_key=settings.MINIO_SECRET_KEY,
    config=Config(signature_version='s3v4')
)

BUCKET_NAME = settings.MINIO_BUCKET_NAME

def create_minio_bucket_if_not_exists():
    try:
        s3_client.head_bucket(Bucket=BUCKET_NAME)
        print(f"Bucket '{BUCKET_NAME}' already exists.")
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            print(f"Bucket '{BUCKET_NAME}' not found. Creating it.")
            s3_client.create_bucket(Bucket=BUCKET_NAME)
            print(f"Bucket '{BUCKET_NAME}' created.")
        else:
            print("Error checking for bucket:")
            raise

def upload_file_obj(file_obj, object_name: str):
    try:
        s3_client.upload_fileobj(file_obj, BUCKET_NAME, object_name)
    except ClientError as e:
        print(f"Error uploading to MinIO: {e}")
        return False
    return True

def download_file(object_name: str, file_path: str):
    try:
        s3_client.download_file(BUCKET_NAME, object_name, file_path)
    except ClientError as e:
        print(f"Error downloading from MinIO: {e}")
        return False
    return True

def delete_file(object_name: str):
    try:
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=object_name)
    except ClientError as e:
        print(f"Error deleting from MinIO: {e}")
        return False
    return True