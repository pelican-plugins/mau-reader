import os

from mau_reader import MauReader
from pelican.tests.support import get_settings

DIR_PATH = os.path.dirname(__file__)
TEST_CONTENT_PATH = os.path.abspath(os.path.join(DIR_PATH, "test_data"))


def header_anchor(text, level):
    return "ANCHOR"


def test_article_with_mau_extension():
    settings = get_settings()

    settings["MAU"] = {
        "mau": {
            "parser": {
                "header_anchor_function": header_anchor,
            },
            "visitor": {
                "custom_templates": {
                    "header.html": (
                        '<h{{ level }} id="ANCHOR">'
                        "{{ value }}"
                        '{% if anchor %}<a href="#ANCHOR">¶</a>{% endif %}'
                        "</h{{ level }}>"
                    )
                }
            },
        },
    }

    mau_reader = MauReader(settings)

    source_path = os.path.join(TEST_CONTENT_PATH, "article_with_content.mau")
    output, metadata = mau_reader.read(source_path)

    with open(os.path.join(TEST_CONTENT_PATH, "article_with_content.html")) as f:
        expected = f.read().strip()

    assert output == expected


def test_article_with_mau_extension_metadata():
    settings = get_settings()
    mau_reader = MauReader(settings)

    source_path = os.path.join(TEST_CONTENT_PATH, "article_with_content.mau")
    output, metadata = mau_reader.read(source_path)

    assert metadata["title"] == "Test Mau file with content"
    assert metadata["date"].strftime("%Y-%m-%d %H:%M:%S") == "2021-02-17 13:00:00"
    assert metadata["modified"].strftime("%Y-%m-%d %H:%M:%S") == "2021-02-17 14:00:00"
    assert metadata["category"] == "test"
    assert [str(i) for i in metadata["tags"]] == ["foo", "bar", "foobar"]
    assert metadata["summary"] == "<p>I have a lot to test</p>"


def test_article_with_mau_extension_non_ascii_metadata():
    settings = get_settings()
    mau_reader = MauReader(settings)

    source_path = os.path.join(TEST_CONTENT_PATH, "article_with_nonascii_metadata.mau")
    output, metadata = mau_reader.read(source_path)

    assert metadata["title"] == "マックOS X 10.8でパイソンとVirtualenvをインストールと設定"
    assert metadata["date"].strftime("%Y-%m-%d %H:%M:%S") == "2012-12-20 00:00:00"
    assert metadata["modified"].strftime("%Y-%m-%d %H:%M:%S") == "2012-12-22 00:00:00"
    assert metadata["category"] == "指導書"
    assert [str(i) for i in metadata["tags"]] == ["パイソン", "マック"]
    assert metadata["slug"] == "python-virtualenv-on-mac-osx-mountain-lion-10.8"
