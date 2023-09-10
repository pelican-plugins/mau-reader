"""Mau Reader plugin.

This plugin allows you to use Mau to write your posts. File extension should be `.mau`.

"""

from typing import ClassVar, List

from pelican import signals
from pelican.readers import BaseReader
from pelican.utils import pelican_open

try:
    from mau import Mau, load_visitors

    visitor_classes = load_visitors()
    mau_enabled = True
except ImportError:
    visitor_classes = []
    mau_enabled = False


visitors = {i.format_code: i for i in visitor_classes}


class OutputFormatNotSupported(Exception):
    """Exception to signal output format not supported."""

    def __init__(self, output_format):
        super().__init__(
            f"Output format {output_format} is not supported by Mau. "
            "You might have to install a plugin."
        )


class MauReader(BaseReader):
    """Mau Reader class method."""

    enabled = mau_enabled
    file_extensions: ClassVar[List[str]] = ["mau"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def read(self, source_path):
        config = self.settings.get("MAU", {})

        output_format = config.get("output_format", "html")

        if output_format not in visitors:
            raise OutputFormatNotSupported(output_format)

        custom_templates = config.get("custom_templates", {})
        templates_directory = config.get("templates_directory", None)
        visitor_class = visitors[output_format]

        self._source_path = source_path
        self._mau = Mau(
            source_path,
            visitor_class=visitor_class,
            config=config,
            custom_templates=custom_templates,
            templates_directory=templates_directory,
        )

        with pelican_open(source_path) as text:
            lexer = self._mau.run_lexer(text)

        parser = self._mau.run_parser(lexer.tokens)
        content = self._mau.process(parser.nodes, parser.environment)

        if visitor_class.transform:
            content = visitor_class.transform(content)

        metadata = self._parse_metadata(self._mau.environment.asdict()["pelican"])

        return content, metadata

    def _parse_metadata(self, meta):
        """Return the dict containing document metadata."""
        formatted_fields = self.settings["FORMATTED_FIELDS"]

        output = {}
        for name, value in meta.items():
            name = name.lower()
            if name in formatted_fields:
                lexer = self._mau.run_lexer(value)
                parser = self._mau.run_parser(lexer.tokens)
                formatted = self._mau.process(parser.nodes, parser.environment)
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
