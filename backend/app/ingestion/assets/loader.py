import hashlib
import io
import mimetypes
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.ingestion.assets.image_asset import ImageAsset
from app.ingestion.exceptions import LoaderError


class AssetLoader:
    """Reads a binary media file off disk into an Asset (metadata only) plus
    the raw bytes needed for *immediate* analysis. The bytes are returned to
    the caller and never retained here or on the Asset model itself - callers
    must not persist them beyond a single ingest call."""

    def load_image(self, path: str) -> tuple[ImageAsset, bytes]:
        file_path = Path(path)
        if not file_path.is_file():
            raise LoaderError(f"Image asset not found: '{path}'")

        raw = file_path.read_bytes()
        try:
            with Image.open(io.BytesIO(raw)) as image:
                width, height = image.size
                image_format = image.format
        except UnidentifiedImageError as exc:
            raise LoaderError(f"'{path}' is not a readable image: {exc}") from exc

        mime_type = mimetypes.guess_type(path)[0] or (
            f"image/{image_format.lower()}" if image_format else "application/octet-stream"
        )

        asset = ImageAsset(
            source=path,
            filename=file_path.name,
            mime_type=mime_type,
            size=len(raw),
            checksum=hashlib.sha256(raw).hexdigest(),
            created_at=datetime.now(UTC),
            width=width,
            height=height,
        )
        return asset, raw
