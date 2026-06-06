import boto3
import httpx
from app import config

TTS_URL = "https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts"

def _call_clova_voice(text: str) -> bytes:
    """CLOVA Voice 호출. mp3 바이너리 반환. 테스트에서 mock 된다."""
    # 음성 전용 키(NCP_VOICE_*)가 있으면 우선 사용, 없으면 공용 APIGW 키로 폴백.
    # (CLOVA Voice 를 Papago 와 다른 Application 으로 등록한 경우 NCP_VOICE_* 사용)
    headers = {
        "X-NCP-APIGW-API-KEY-ID": config.get_env_or("NCP_VOICE_KEY_ID", "NCP_APIGW_KEY_ID"),
        "X-NCP-APIGW-API-KEY": config.get_env_or("NCP_VOICE_KEY", "NCP_APIGW_KEY"),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"speaker": "nara", "text": text[:1900], "format": "mp3"}  # 길이 제한 보호
    resp = httpx.post(TTS_URL, headers=headers, data=data, timeout=30.0)
    resp.raise_for_status()
    return resp.content

def _upload_to_storage(data: bytes, key: str) -> str:
    """Object Storage(S3 호환)에 업로드 후 공개 URL 반환. 테스트에서 mock 된다."""
    endpoint = config.get_env("NCP_OS_ENDPOINT")
    bucket = config.get_env("NCP_OS_BUCKET")
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name="kr-standard",  # NCP Object Storage(KR) 기본 리전 — boto3 region 누락 오류 방지
        aws_access_key_id=config.get_env("NCP_OS_ACCESS_KEY"),
        aws_secret_access_key=config.get_env("NCP_OS_SECRET_KEY"),
    )
    client.put_object(Bucket=bucket, Key=key, Body=data, ContentType="audio/mpeg", ACL="public-read")
    # path-style 공개 URL. NCP 콘솔에서 엔드포인트/접근 방식 확정 후 필요시 조정.
    return f"{endpoint}/{bucket}/{key}"

def synthesize_and_upload(text: str, key: str) -> str | None:
    if not text or not text.strip():
        return None
    audio = _call_clova_voice(text)
    return _upload_to_storage(audio, key)
