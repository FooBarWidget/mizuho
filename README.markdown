# Mizuho documentation formatting tool

Mizuho is a documentation formatting tool, best suited for small to
medium-sized documentation. One writes documentation in plain text
files, which Mizuho then converts to nicely formatted HTML.

Mizuho wraps [Asciidoc](http://www.methods.co.nz/asciidoc/), the text
formatting tool used by e.g. Git and Phusion Passenger for its manuals.
Mizuho adds the following functionality on top of Asciidoc:

 * Commenting via [Juvia](https://github.com/FooBarWidget/juvia).

Mizuho bundles Asciidoc so you don't have to install it yourself. Mizuho
should Just Work(tm) out-of-the-box. Asciidoc uses GNU source-highlight
for highlighting source code. GNU source-highlight depends on Boost and
so is notorious for being difficult to install on systems without a
decent package manager (e.g. OS X). Mizuho comes prebundled with an OS
X binary for GNU source-highlight so that you don't have to worry about
that.

## Requirements

 * Nokogiri (`gem install nokogiri`)
 * Python (because Asciidoc is written in Python)
 * [GNU Source-highlight](http://www.gnu.org/software/src-highlite/), if you
   want syntax highlighting support. If you're on OS X then it's not necessary
   to install this yourself; we've bundled a precompiled source-highlight
   binary for OS X for your convenience.

## Installation

Run the following command as root:

    gem install mizuho

## Usage

First, read the Asciidoc manual to learn the input file format:
http://www.methods.co.nz/asciidoc/userguide.html

Next, write an input file and save it in a .txt file.

Finally, convert the .txt file to a single HTML file with Mizuho, with the
default template:

    mizuho input.txt

This will generate 'input.html'.

## Credits

This tool is named after Kazami Mizuho from the 2003 anime 'Onegai Teacher'.
