"""Mau Reader plugin.

This plugin allows you to use Mau to write your posts. File extension should be `.mau`.

"""

from logging import WARNING, getLogger
import re

from pelican import signals
from pelican.readers import BaseReader
from pelican.utils import pelican_open

logger = getLogger(__name__)


try:
    from mau import BASE_NAMESPACE, Mau, load_visitors
    from mau.environment.environment import Environment
    from mau.message import LogMessageHandler, MauException

    # Load a dictionary of all visitors,
    # indexed by the output format.
    visitors = load_visitors()
    mau_enabled = True
except ImportError:
    visitors = {}
    mau_enabled = False

# This is the additional namespace
# used by elements that are rendered for
# the entire page and not just for the
# document, like the metadata ToC.
DEFAULT_PAGE_NAMESPACE = "page"


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


def _text_to_name(text: str | None) -> str | None:
    if not text:
        return text

    # The input text can contain spaces an mixed-case
    # characters. Convert it into lowercase.
    text = text.lower()

    # Replace spaces and underscores with dashes.
    text = re.sub(r"[\ _]+", "-", text)

    # Get only letters, numbers, dashes.
    return "".join(re.findall("[a-z0-9-\\. ]+", text))


class MauReader(BaseReader):
    """Mau Reader class method."""

    enabled = mau_enabled
    file_extensions = ("mau",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # The message handler uses the Pelican
        # logger to send messages.
        self.message_handler = LogMessageHandler(logger, debug_logging_level=WARNING)

    def read(self, source_path):
        # Import Mau settings from Pelican settings
        mau_config_dict = self.settings.get("MAU", {})

        # Load the Mau configuration under
        # the base namespace.
        environment = Environment.from_dict(mau_config_dict, BASE_NAMESPACE)

        # Get the Mau configuration as an environment.
        config = environment.get(BASE_NAMESPACE)

        # Load Mau variables from Pelican settings
        mau_variables = Environment.from_dict(self.settings.get("MAU_VARIABLES", {}))

        # Update the environment adding the variables.
        environment.update(mau_variables, overwrite=False)

        # Extract the selected visitor or use the
        # HTML visitor from the standard plugin.
        selected_visitor = config.get(
            "mau.visitor.name", "mau_html_visitor:HtmlVisitor"
        )

        # If the selected visitor is not available
        # we need to stop and sound the alarm.
        if selected_visitor not in visitors:
            raise OutputFormatNotSupported(selected_visitor)

        # Let's store the selected visitor class.
        # We will need it when we parse the
        # metadata later.
        self.visitor_class = visitors[selected_visitor]

        # This is stored in a variable to
        # be available inside documents.
        environment["mau.visitor.format"] = self.visitor_class.format_code

        # This is another value we need later.
        self._source_path = source_path

        # Instantiate the Mau object.
        mau = Mau(self.message_handler, environment=environment)

        # The following code processes the
        # Pelican input document.
        # It is a giant try/except because
        # so many things can go wrong and in
        # all those cases Pelican needs to
        # know what and to move on.
        try:
            # Read the source file and instantiate
            # a text buffer on it.
            with pelican_open(source_path) as text:
                # Initialise the Text Buffer.
                text_buffer = mau.init_text_buffer(text, source_path)

            # Lex and parse the input document.
            lexer = mau.run_lexer(text_buffer)
            parser = mau.run_parser(lexer.tokens)

            # Pelican allows to store metadata
            # in the document file itself, so
            # we need to save the environment
            # AFTER the parsing, which contains
            # the configuration we created above
            # plus any variable created in the
            # document.
            self.environment = mau.environment

            # Mau allows us to define custom
            # prefixes for templates. This reader
            # uses the Pelican template and the
            # Pelican series as prefixes. This
            # means that we can customise Mau
            # templates according to the Pelican
            # series or the Pelican template.

            # The list of custom Mau prefixes.
            prefixes = []

            # This is the name of the Pelican series.
            # The name of a series can contain spaces
            # and other characters that do not sit well
            # with file naming for Mau templates.
            # This is why we process it to transform it
            # into a usable name.
            prefixes.append(_text_to_name(self.environment.get("pelican.series")))

            # This is the name of the Pelican template.
            prefixes.append(self.environment.get("pelican.template"))

            # Filter out any invalid value.
            prefixes = [i for i in prefixes if i is not None]

            # Store the prefixes into the environment.
            self.environment["mau.visitor.templates.prefixes"] = prefixes

            # Get the main output node from the parser.
            document = parser.output.document

            # Process the node with the
            # selected visitor.
            content = mau.run_visitor(self.visitor_class, document)

            # Process the Pelican metadata.
            # This returns a dictionary
            # {metadata: processed value}
            metadata = self._parse_metadata()

            # Add the ToC as metadata, so that
            # it is available to Pelican and can
            # be addedd to the page outside
            # the rendered document itself
            # (e.g. in a sidebar).

            # From this point, all custom prefixes
            # created before (Pelican template and series)
            # are given the additional namespace `page`
            # to signal that the rendered text belongs
            # to the page and not the document.
            prefixes = [f"{DEFAULT_PAGE_NAMESPACE}-{i}" for i in prefixes]
            prefixes.append(DEFAULT_PAGE_NAMESPACE)

            # Store the prefixes into the environment.
            self.environment["mau.visitor.templates.prefixes"] = prefixes

            # Create Mau metadata inside the Pelican metadata.
            metadata["mau"] = {
                # Add the rendered nested ToC to the metadata.
                "toc": mau.run_visitor(self.visitor_class, parser.output.toc)
            }

        except MauException as exception:
            self.message_handler.process(exception.message)
            raise ErrorInSourceFile(source_path) from exception

        return content, metadata

    def _parse_metadata(self):
        # Finds metadata defined inside the document,
        # process it, collect it into a dictionary,
        # and return it.

        # All Pelican metadata must be
        # defined under the namespace
        # `pelican`.
        pelican_env = self.environment.get("pelican")
        meta = pelican_env.asdict() if pelican_env is not None else {}

        # Get from Pelican the list of fields
        # that support formatting (i.e. rich text).
        formatted_fields = self.settings["FORMATTED_FIELDS"]

        # Instantiate the Mau object.
        mau = Mau(self.message_handler, environment=self.environment)

        # This is the final dictionary
        # of processed metadata.
        output = {}

        # For each metadata variable defined
        # in the document, extract name and value,
        # process the value if needed, and store
        # it in the final dictionary.
        for name, value in meta.items():
            # Lowercase all metadata.
            name = name.lower()

            if name in formatted_fields:
                # For debugging purposes, change the
                # source path adding the metadata field
                # we are processing.
                source_path = f"{self._source_path}::{name}"

                # Process the value of the metadata field.
                content = mau.process(self.visitor_class, value, source_path)

                # Add it to the final output.
                output[name] = self.process_metadata(name, content)

                continue

            # The value is a plain string from
            # Mau's Environment. Pass it directly
            # to Pelican's metadata processing.
            output[name] = self.process_metadata(name, value)

        return output


def add_reader(readers):
    """Register Mau reader."""
    for ext in MauReader.file_extensions:
        readers.reader_classes[ext] = MauReader


def register():
    """Register Mau Reader plugin."""
    signals.readers_init.connect(add_reader)
