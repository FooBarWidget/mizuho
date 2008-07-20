= Mizuho documentation formatting tool

Mizuho is a documentation formatting tool, best suited for small to
medium-sized documentation. One writes documentation in plain text
files, which Mizuho then converts to nicely formatted HTML.

Mizuho supports input files in Asciidoc format. Asciidoc is a text
formatting tool, used by e.g. Git for its documentation. Thanks to Asciidoc,
Mizuho supports a large number of formatting options.

Asciidoc: http://www.methods.co.nz/asciidoc/

=== Under the hood

Mizuho is actually a wrapper around Asciidoc. Asciidoc itself can only
generate single-page XHTML output. Mizuho extends Asciidoc by providing
multi-page XHTML output support and support for multiple templates.

== Features and highlights

* You can output the documentation in a single XHTML file, or in multiple
  XHTML files (one per chapter).
* Output is fully customizable via ERB templates.
* Based on Asciidoc and supports all Asciidoc formatting commands.
* Comes bundled with Asciidoc so you don't have to install it yourself. Mizuho
  Just Works(tm) out-of-the-box.

== Requirements

* hpricot
* Python (because Asciidoc is written in Python)
* GNU Source-highlight, if you want syntax highlighting support:
  http://www.gnu.org/software/src-highlite/

== Installation

 gem install --source http://gems.github.com FooBarWidget-mizuho

== Usage

First, read the Asciidoc manual to learn the input file format:
http://www.methods.co.nz/asciidoc/userguide.html

Next, write an input file and save it in a .txt file.

Finally, convert the .txt file to a single XHTML file with Mizuho, with the
default template:

  mizuho input.txt

This will generate 'input.html'. Or, you can convert it to multiple XHTML files
that also have a different look:

  mizuho input.txt --template manualsonrails --multi-page

Take a look at the 'templates' directory for available templates.

== Credits

This tool is named after Kazami Mizuho from the 2003 anime 'Onegai Teacher'.
