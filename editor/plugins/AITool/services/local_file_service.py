import base64
import mimetypes
from pathlib import Path


class LocalFileService:
    @staticmethod
    def read_as_base64(file_url: str) -> str:
        try:
            file_path = file_url[7:] if file_url.startswith("file://") else file_url
            path = Path(file_path)
            if not path.exists() or not path.is_file():
                print(f"文件不存在: {file_path}")
                return ""

            file_data = path.read_bytes()
            mime_type, _ = mimetypes.guess_type(str(path))
            if not mime_type:
                mime_type = LocalFileService._guess_mime_type(path)

            base64_data = base64.b64encode(file_data).decode("utf-8")
            return f"data:{mime_type};base64,{base64_data}"
        except Exception as exc:
            print(f"读取文件失败: {exc}")
            return ""

    @staticmethod
    def _guess_mime_type(path: Path) -> str:
        ext = path.suffix.lower()
        if ext in [".mp4", ".webm", ".ogg"]:
            return f"video/{ext[1:]}"
        if ext in [".mp3", ".wav", ".m4a"]:
            return f"audio/{ext[1:]}"
        return "application/octet-stream"