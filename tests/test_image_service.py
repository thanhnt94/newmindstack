import sys
import types


if "duckduckgo_search" not in sys.modules:
    duckduckgo_search = types.ModuleType("duckduckgo_search")

    class _StubDuckDuckGoSearchException(Exception):
        pass

    class _StubDDGS:  # pragma: no cover - chỉ dùng làm stub môi trường test
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def images(self, *_args, **_kwargs):
            return []

    duckduckgo_search.DDGS = _StubDDGS
    exceptions_module = types.ModuleType("duckduckgo_search.exceptions")
    exceptions_module.DuckDuckGoSearchException = _StubDuckDuckGoSearchException
    sys.modules["duckduckgo_search"] = duckduckgo_search
    sys.modules["duckduckgo_search.exceptions"] = exceptions_module

from duckduckgo_search.exceptions import DuckDuckGoSearchException

from mindstack_app.config import Config
from mindstack_app.modules.learning.sub_modules.flashcard_learning.image_service import ImageService


class _FailingContextManager:
    def __init__(self, exception: Exception):
        self._exception = exception

    def __enter__(self):
        raise self._exception

    def __exit__(self, exc_type, exc, tb):
        return False


def test_get_cached_or_download_image_retries_on_duckduckgo_exception(monkeypatch, tmp_path):
    original_upload = Config.UPLOAD_FOLDER
    original_cache = Config.FLASHCARD_IMAGE_CACHE_DIR

    try:
        monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path))
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(Config, "FLASHCARD_IMAGE_CACHE_DIR", str(cache_dir))

        failure = DuckDuckGoSearchException("Rate limit reached")
        monkeypatch.setattr(
            "mindstack_app.modules.learning.flashcard_learning.image_service.DDGS",
            lambda: _FailingContextManager(failure),
        )

        sleep_calls = {"count": 0}

        def fake_sleep(seconds):
            sleep_calls["count"] += 1

        monkeypatch.setattr(
            "mindstack_app.modules.learning.flashcard_learning.image_service.time.sleep",
            fake_sleep,
        )

        service = ImageService()

        result = service.get_cached_or_download_image("test query")

        assert result == (
            None,
            False,
            "Dịch vụ tìm kiếm ảnh đang bận, vui lòng thử lại sau.",
        )
        assert sleep_calls["count"] == 2
    finally:
        setattr(Config, "UPLOAD_FOLDER", original_upload)
        setattr(Config, "FLASHCARD_IMAGE_CACHE_DIR", original_cache)


