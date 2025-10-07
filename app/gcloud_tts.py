import os, uuid, boto3
from google.cloud import texttospeech
from botocore.exceptions import BotoCoreError, ClientError

GCP_VOICE = os.getenv("GCP_TTS_VOICE", "en-US-Wavenet-D")
GCP_LANG = os.getenv("GCP_TTS_LANGUAGE_CODE", "en-US")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("AWS_S3_BUCKET")

s3_client = boto3.client("s3", region_name=AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

def synthesize_gcloud_tts_to_s3(text: str, voice: str = None, filename: str = None, bucket: str = None, fmt: str = "mp3") -> str:
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice_config = texttospeech.VoiceSelectionParams(language_code=GCP_LANG, name=voice or GCP_VOICE)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(input=synthesis_input, voice=voice_config, audio_config=audio_config)
    audio_content = response.audio_content
    bucket = bucket or S3_BUCKET
    if not bucket:
        raise ValueError("S3 bucket name is not configured (AWS_S3_BUCKET).")
    filename = filename or f"gctts_{uuid.uuid4().hex}.{fmt}"
    try:
        s3_client.put_object(Bucket=bucket, Key=filename, Body=audio_content, ACL='public-read', ContentType='audio/mpeg')
    except Exception as e:
        raise RuntimeError(f"S3 upload failed: {e}") from e
    return f"https://{bucket}.s3.{AWS_REGION}.amazonaws.com/{filename}"
