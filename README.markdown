# Mizuho documentation formatting tool

Mizuho is a documentation formatting tool, best suited for small to
medium-sized documentation. One writes documentation in plain text
files, which Mizuho then converts to nicely formatted HTML.

Mizuho wraps [Asciidoc](http://www.methods.co.nz/asciidoc/), the text
formatting tool used by e.g. Git and Phusion Passenger for its manuals.
Mizuho adds the following functionality on top of Asciidoc:

 * A top bar that gives quick access to the table of contents.
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

## Installation with RubyGems

Run:

    gem install mizuho

This gem is signed using PGP with the [Phusion Software Signing key](http://www.phusion.nl/about/gpg). That key in turn is signed by [the rubygems-openpgp Certificate Authority](http://www.rubygems-openpgp-ca.org/).

You can verify the authenticity of the gem by following [The Complete Guide to Verifying Gems with rubygems-openpgp](http://www.rubygems-openpgp-ca.org/blog/the-complete-guide-to-verifying-gems-with-rubygems-openpgp.html).

## Installation on Ubuntu

Use our [PPA](https://launchpad.net/~phusion.nl/+archive/misc):

    sudo add-apt-repository ppa:user/ppa-name
    sudo apt-get update
    sudo apt-get install mizuho

## Installation on Debian

Our Ubuntu Lucid packages are compatible with Debian 6.

    sudo sh -c 'echo deb http://ppa.launchpad.net/phusion.nl/misc/ubuntu lucid main > /etc/apt/sources.list.d/mizuho.list'
    sudo sh -c 'echo deb-src http://ppa.launchpad.net/phusion.nl/misc/ubuntu lucid main >> /etc/apt/sources.list.d/mizuho.list'
    sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys C324F5BB38EEB5A0
    sudo apt-get update
    sudo apt-get install mizuho

## Usage

First, read [the Asciidoc manual](http://www.methods.co.nz/asciidoc/userguide.html)
to learn the input file format:

Next, write an input file and save it in a .txt file.

Finally, convert the .txt file to a single HTML file with Mizuho, with the
default template:

    mizuho input.txt

This will generate 'input.html'.

### Commenting via Juvia

To enable commenting via Juvia, pass `-c juvia` and the `--juvia-url` and
`--juvia-site-key` arguments with appropriate values. Mizuho will generate a
so-called *ID map file* if there isn't already one. This file maps section
titles to Juvia topic IDs. This way you can preserve a section's comments
even when you rename that section's title. Note that the section's number is
considered part of the title, so renaming can happen implicitly.

When a section title has been renamed, Mizuho will look for a Juvia topic ID
for which the previous title is similar to the new title, and assign that ID
to the section. The entry in the ID map file is then marked 'fuzzy' in order to
warn you about this. You have to remove the `# fuzzy` comment in the ID map
file, or Mizuho will keep complaining about this in subsequent runs.

## Credits

This tool is named after Kazami Mizuho from the 2003 anime 'Onegai Teacher'.
