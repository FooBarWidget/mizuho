Source: mizuho
Section: text
Priority: optional
Maintainer: Hongli Lai <hongli@phusion.nl>
Build-Depends: debhelper (>= 7.0.50~), gem2deb (>= 0.2.0~), sed (>= 1.0.0)
Standards-Version: 3.9.3
Homepage: https://github.com/FooBarWidget/mizuho
Vcs-Git: git://github.com/FooBarWidget/mizuho.git
Vcs-Browser: https://github.com/FooBarWidget/mizuho
XS-Ruby-Versions: all

Package: mizuho
Architecture: all
XB-Ruby-Versions: ${ruby:Versions}
#if is_distribution?('>= precise')
    Depends: ${shlibs:Depends}, ${misc:Depends}, ruby | ruby-interpreter, ruby-nokogiri (>= 1.4.0), source-highlight, asciidoc (>= 8.6.0)
#else
    Depends: ${shlibs:Depends}, ${misc:Depends}, ruby | ruby-interpreter, libnokogiri-ruby (>= 1.4.0), source-highlight
#endif
Description: Documentation formatting tool
 Converts Asciidoc input files into nicely
 outputted HTML, possibly one file per chapter.
