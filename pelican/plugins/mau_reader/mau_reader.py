"""Mau Reader plugin.

This plugin allows you to use Mau to write your posts. File extension should be `.mau`.

"""

from pelican import signals
from pelican.readers import BaseReader
from pelican.utils import pelican_open

try:
    from mau import Mau, load_visitors
    from mau.environment.environment import Environment
    from mau.errors import MauErrorException, print_error

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


class ErrorInSourceFile(Exception):
    """Exception to signal an error parsing the source file."""

    def __init__(self, filename):
        super().__init__(f"The file {filename} cannot be parsed")


class MauReader(BaseReader):
    """Mau Reader class method."""

    enabled = mau_enabled
    file_extensions = ("mau",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def read(self, source_path):
        self.environment = Environment()
        config = self.settings.get("MAU", {})

        output_format = config.get("output_format", "html")

        if output_format not in visitors:
            raise OutputFormatNotSupported(output_format)

        visitor_class = visitors[output_format]
        self.environment.setvar("mau.visitor.class", visitor_class)
        self.environment.setvar("mau.visitor.format", output_format)

        # Import Mau settings from Pelican settings
        self.environment.update(self.settings.get("MAU", {}))

        self._source_path = source_path

        mau = Mau(
            source_path,
            self.environment,
        )

        try:
            with pelican_open(source_path) as text:
                mau.run_lexer(text)

            # Run the Mau parser
            mau.run_parser(mau.lexer.tokens)

            # These are the templates prefixes
            prefixes = [
                self.environment.getvar("pelican.series"),
                self.environment.getvar("pelican.template"),
            ]
            prefixes = [i for i in prefixes if i is not None]
            self.environment.setvar("mau.visitor.prefixes", prefixes)

            # Run the visitor on the main content
            content = mau.run_visitor(mau.parser.output["content"])
            if visitor_class.transform:
                content = visitor_class.transform(content)

            metadata = self._parse_metadata()

            prefixes = [f"{i}.page" for i in prefixes] + ["page"]
            self.environment.setvar("mau.visitor.prefixes", prefixes)

            metadata["mau"] = {}
            metadata["mau"]["toc"] = mau.run_visitor(mau.parser.output["toc"])

        except MauErrorException as exception:
            print_error(exception.error)

            raise ErrorInSourceFile(source_path) from exception

        return content, metadata

    def _parse_metadata(self):
        """Return the dict containing document metadata."""
        meta = self.environment.getvar("pelican").asdict()

        formatted_fields = self.settings["FORMATTED_FIELDS"]

        mau = Mau(
            self._source_path,
            self.environment,
        )

        output = {}
        for name, value in meta.items():
            name = name.lower()
            if name in formatted_fields:
                mau.run_lexer(value)
                mau.run_parser(mau.lexer.tokens)
                formatted = mau.run_visitor(mau.parser.output["content"])
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
