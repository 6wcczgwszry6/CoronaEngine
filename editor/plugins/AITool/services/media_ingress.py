class MediaIngress:
    def __init__(self, base64_to_image_file, upload_file_to_server):
        self._base64_to_image_file = base64_to_image_file
        self._upload_file_to_server = upload_file_to_server

    def prepare_payload(self, payload: dict) -> tuple[dict, str | None]:
        self._upload_images(payload)
        token = self._extract_token(payload)
        return payload, token

    def _upload_images(self, payload: dict):
        llm_content = payload.get("llm_content", [])
        if not isinstance(llm_content, list):
            return
        for content in llm_content:
            if not isinstance(content, dict):
                continue
            parts = content.get("part", [])
            if not isinstance(parts, list):
                continue
            for part in parts:
                if isinstance(part, dict) and part.get("content_type") == "image":
                    part["content_url"] = self._upload_file_to_server(
                        self._base64_to_image_file(part.get("content_url", ""))
                    )

    @staticmethod
    def _extract_token(payload: dict) -> str | None:
        token = payload.pop("token", None)
        metadata = payload.get("metadata")
        if isinstance(metadata, dict) and "token" in metadata:
            token = metadata.pop("token") or token
        return token if isinstance(token, str) else None
