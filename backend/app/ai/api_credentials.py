"""Read provider keys from SSM on job hosts; never expose values in errors."""
import os
import time
from functools import lru_cache

from app.ai.base import ProviderCallError


@lru_cache(maxsize=8)
def _read(prefix, name, window):
    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError
    try:
        return boto3.client("ssm", config=Config(connect_timeout=3, read_timeout=5,
                    retries={"total_max_attempts": 2})).get_parameter(
            Name=f"{prefix}/{name}", WithDecryption=True,
        )["Parameter"]["Value"]
    except (BotoCoreError, ClientError) as exc:
        raise ProviderCallError("The provider credential could not be loaded.", retryable=False) from exc


def provider_key(name, fallback=""):
    prefix = os.environ.get("MODEL_KEYS_SSM_PREFIX")
    return _read(prefix, name, int(time.time() // 60)) if prefix else fallback
