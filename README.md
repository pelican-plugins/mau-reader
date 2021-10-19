# Mau Reader: A Plugin for Pelican

[![Build Status](https://img.shields.io/github/workflow/status/pelican-plugins/mau-reader/build)](https://github.com/pelican-plugins/mau-reader/actions)
[![PyPI Version](https://img.shields.io/pypi/v/pelican-mau-reader)](https://pypi.org/project/pelican-mau-reader/)
![License](https://img.shields.io/pypi/l/pelican-mau-reader?color=blue)

Mau Reader is a Pelican plugin that converts the [Mau](https://github.com/Project-Mau/mau) format into HTML.

## Requirements

This plugin requires:

* Python 3.6+
* Pelican 4.5+
* Mau 2.0+

## Installation

This plugin can be installed via the following command, which will also automatically install Mau itself:

    python -m pip install pelican-mau-reader

## Usage

The plugin automatically manages all Pelican content files ending with the extension: `.mau`

Metadata shall be expressed as Mau variables under the `pelican` namespace. For example:

```
:pelican.title:Test Mau file with content
:pelican.date:2021-02-17 13:00:00
:pelican.modified:2021-02-17 14:00:00
:pelican.category:test
:pelican.tags:foo, bar, foobar
:pelican.summary:I have a lot to test
```

The value of a metadata field is a string, just as it is in the standard Markdown format. Please note that Mau variable values include all characters after the colon, spaces included.

All values in the `config` dictionary are available as variables, so you can specify global values that are valid for all documents.

## Custom templates

You can override some or all Mau default HTML templates via the `custom_templates` configuration variable. For example, should you want to add a permanent link to all headers you can define:

``` python
MAU = {
    "custom_templates": {
        "header.html": (
            '<h{{ level }} id="{{ anchor }}">'
            "{{ value }}"
            '<a href="#{{ anchor }}" title="Permanent link">¶</a>'
            "</h{{ level }}>"
        )
    }
}
```

… and if you want to limit that to only headers of level 1 and 2 you can use:

``` python
MAU = {
    "custom_templates": {
        "header.html": (
            '<h{{ level }} id="{{ anchor }}">'
            "{{ value }}"
            '{% if level <= 2 %}<a href="#{{ anchor }}" title="Permanent link">¶</a>{% endif %}'
            "</h{{ level }}>"
        )
    }
}
```

## Table of contents and footnotes

The TOC (Table of Contents) and footnotes are specific to each content file and can be inserted as usual with the Mau commands `::toc:` and `::footnotes:`.

## Custom header anchors

Mau provides a simple function to compute IDs for headers, based on the content. The current function is:

``` python
def header_anchor(text, level):
    # Everything lowercase
    sanitised_text = text.lower()

    # Get only letters, numbers, dashes, and spaces
    sanitised_text = "".join(re.findall("[a-z0-9- ]+", sanitised_text))

    # Remove multiple spaces
    sanitised_text = "-".join(sanitised_text.split())

    return sanitised_text
```

This provides deterministic header IDs that should suit the majority of cases. Should you need something different, you can provide your own function specifying `mau.header_anchor_function` in the configuration:

``` python
MAU = {
    "mau.header_anchor_function": lambda text, level: "XYZ",
}
```

The example above returns the ID `XYZ` for all headers (not recommended as it is not unique). The arguments `text` and `level` are respectively the text of the header itself and an integer representing the level of depth (e.g., `1` for `h1` headers, `2` for `h2` headers, and so on).

## Contributing

Contributions are welcome and much appreciated. Every little bit helps. You can contribute by improving the documentation, adding missing features, and fixing bugs. You can also help out by reviewing and commenting on [existing issues][].

To start contributing to this plugin, review the [Contributing to Pelican][] documentation, beginning with the **Contributing Code** section.

[existing issues]: https://github.com/pelican-plugins/mau-reader/issues
[Contributing to Pelican]: https://docs.getpelican.com/en/latest/contribute.html

## License

This project is licensed under the MIT license.
