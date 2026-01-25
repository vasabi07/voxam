import boto3
from botocore.client import Config
import httpx
import os
import uuid

async def get_file(file_key: str, expires_in: int = 60):
    session = boto3.session.Session()
    r2 = session.client(
        service_name='s3',
        region_name='auto',
        endpoint_url=os.environ['R2_ENDPOINT'],
        aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],
        config=Config(signature_version='s3v4'),
    )
    signed_url = r2.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': os.environ['R2_BUCKET'],
            'Key': file_key,
        },
        ExpiresIn=expires_in
    )

    # Create output path - use just the filename, not full key path
    filename = os.path.basename(file_key)
    output_path = f"./content/{filename}"
    os.makedirs("./content", exist_ok=True)

    async with httpx.AsyncClient() as client:
        response = await client.get(signed_url)

    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
        return output_path
    else:
        raise Exception(f"Failed to download file: {response.status_code} - {response.text}")