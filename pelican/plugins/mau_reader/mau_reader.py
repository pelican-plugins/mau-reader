"""Mau Reader plugin.

This plugin allows you to use Mau to write your posts. File extension should be `.mau`.
"""

from pelican import signals
from pelican.readers import BaseReader
from pelican.utils import pelican_open

try:
    from mau import Mau

    mau_enabled = True
except ImportError:
    mau_enabled = False


class MauReader(BaseReader):
    """Mau Reader class method."""

    enabled = mau_enabled
    file_extensions = "mau"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def read(self, source_path):
        config = self.settings.get("MAU", {})

        output_format = config.get("output_format", "html")
        custom_templates = config.get("custom_templates", {})

        self._source_path = source_path
        self._mau = Mau(config, output_format, custom_templates=custom_templates)
        with pelican_open(source_path) as text:
            content = self._mau.process(text)

        metadata = self._parse_metadata(self._mau.variables["pelican"])

        return content, metadata

    def _parse_metadata(self, meta):
        """Return the dict containing document metadata."""
        formatted_fields = self.settings["FORMATTED_FIELDS"]

        output = {}
        for name, value in meta.items():
            name = name.lower()
            if name in formatted_fields:
                formatted = self._mau.process(value)
                output[name] = self.process_metadata(name, formatted)
            elif len(value) > 1:
                # handle list metadata as list of string
                output[name] = self.process_metadata(name, value)
            else:
                # otherwise, handle metadata as single string
                output[name] = self.process_metadata(name, value[0])

        return output


def add_reader(readers):
    """Register Mau reader."""
    for ext in MauReader.file_extensions:
        readers.reader_classes[ext] = MauReader


def register():
    """Register Mau Reader plugin."""
    signals.readers_init.connect(add_reader)
