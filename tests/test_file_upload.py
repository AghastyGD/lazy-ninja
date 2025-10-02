from types import SimpleNamespace

from lazy_ninja.file_upload import FileUploadConfig, FileFieldDetector


def test_file_upload_config_accessors():
    config = FileUploadConfig(
        file_fields={"Product": ["image", "manual"]},
        multiple_file_fields={"Product": ["gallery"]},
    )

    assert config.get_model_file_fields("Product") == ["image", "manual"]
    assert config.get_model_file_fields("Unknown") == []
    assert config.get_model_multiple_file_fields("Product") == ["gallery"]
    assert config.is_multiple_file_field("Product", "gallery") is True
    assert config.is_multiple_file_field("Product", "manual") is False


def test_file_field_detector_identifies_single_and_multiple_fields(monkeypatch):
    from lazy_ninja import file_upload

    class StubFileField:
        def __init__(self, name):
            self.name = name

    class StubImageField(StubFileField):
        pass

    class StubManyToManyField:
        def __init__(self, name, related_model):
            self.name = name
            self.related_model = related_model

    monkeypatch.setattr(file_upload, "models", SimpleNamespace(
        FileField=StubFileField,
        ImageField=StubImageField,
        ManyToManyField=StubManyToManyField,
    ))

    related_model = SimpleNamespace(
        _meta=SimpleNamespace(get_fields=lambda: [StubFileField("asset")])
    )

    model = SimpleNamespace(
        _meta=SimpleNamespace(
            get_fields=lambda: [
                StubFileField("document"),
                StubImageField("thumbnail"),
                StubManyToManyField("attachments", related_model),
            ]
        )
    )

    detector = FileFieldDetector()
    single, multiple = detector.detect_file_fields(model)

    assert single == ["document", "thumbnail"]
    assert multiple == ["attachments"]
