import os, boto3, uuid
from botocore.exceptions import BotoCoreError, ClientError

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("AWS_S3_BUCKET")
POLLY_VOICE = os.getenv("POLLY_VOICE", "Joanna")

polly_client = boto3.client("polly", region_name=AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
s3_client = boto3.client("s3", region_name=AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

def synthesize_speech_to_s3(text: str, voice: str = None, filename: str = None, bucket: str = None, fmt: str = "mp3") -> str:
    voice_id = voice or POLLY_VOICE
    bucket = bucket or S3_BUCKET
    if not bucket:
        raise ValueError("S3 bucket name is not configured (AWS_S3_BUCKET).")
    filename = filename or f"tts_{uuid.uuid4().hex}.{fmt}"
    try:
        resp = polly_client.synthesize_speech(Text=text, OutputFormat=fmt, VoiceId=voice_id)
    except Exception as e:
        raise RuntimeError(f"Polly synth failed: {e}") from e
    if "AudioStream" in resp:
        audio_stream = resp["AudioStream"].read()
        try:
            s3_client.put_object(Bucket=bucket, Key=filename, Body=audio_stream, ACL='public-read', ContentType='audio/mpeg')
        except Exception as e:
            raise RuntimeError(f"S3 upload failed: {e}") from e
        return f"https://{bucket}.s3.{AWS_REGION}.amazonaws.com/{filename}"
    else:
        raise RuntimeError("No AudioStream in Polly response.")
