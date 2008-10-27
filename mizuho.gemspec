Gem::Specification.new do |s|
  s.name = "mizuho"
  s.version = "0.9.1"
  s.date = "2008-07-21"
  s.summary = "Mizuho documentation formatting tool"
  s.email = "hongli@phusion.nl"
  s.homepage = "http://github.com/FooBarWidget/mizuho/tree/master"
  s.description = "A documentation formatting tool. Mizuho converts Asciidoc input files into nicely outputted HTML, possibly one file per chapter. Multiple templates are supported, so you can write your own."
  s.has_rdoc = false
  s.executables = ["mizuho"]
  s.authors = ["Hongli Lai"]
  s.add_dependency("hpricot")
  
  s.files = [
      "README.markdown", "LICENSE.txt", "mizuho.gemspec", "Rakefile",
      "bin/mizuho",
      "lib/mizuho/chapter.rb",
      "lib/mizuho/generator.rb",
      "lib/mizuho/heading.rb",
      "lib/mizuho/parser.rb",
      "lib/mizuho/template.rb",
      "test/parser_spec.rb",
      "test/spec_helper.rb",
      "templates/asciidoc.css",
      "templates/asciidoc.html.erb",
      "templates/manualsonrails.css",
      "templates/manualsonrails.html.erb",
      
      "asciidoc/vim/syntax/asciidoc.vim", "asciidoc/vim/ftdetect/asciidoc_filetype.vim", "asciidoc/filters/code-filter.conf", "asciidoc/filters/source-highlight-filter-test.txt", "asciidoc/filters/music-filter.conf", "asciidoc/filters/code-filter-test-c++.txt", "asciidoc/filters/code-filter-test.txt", "asciidoc/filters/source-highlight-filter.conf", "asciidoc/filters/music-filter-test.txt", "asciidoc/filters/code-filter.py", "asciidoc/filters/music2png.py", "asciidoc/filters/code-filter-readme.txt", "asciidoc/stylesheets/xhtml11-manpage.css", "asciidoc/stylesheets/xhtml11-quirks.css", "asciidoc/stylesheets/docbook-xsl.css", "asciidoc/stylesheets/xhtml-deprecated.css", "asciidoc/stylesheets/xhtml-deprecated-manpage.css", "asciidoc/stylesheets/xhtml11.css", "asciidoc/help.conf", "asciidoc/examples/website/downloads.txt", "asciidoc/examples/website/README.html", "asciidoc/examples/website/layout2.conf", "asciidoc/examples/website/support.html", "asciidoc/examples/website/version9.txt", "asciidoc/examples/website/faq.html", "asciidoc/examples/website/index.html", "asciidoc/examples/website/layout2.css", "asciidoc/examples/website/source-highlight-filter.html", "asciidoc/examples/website/a2x.1.html", "asciidoc/examples/website/INSTALL.html", "asciidoc/examples/website/README-website.html", "asciidoc/examples/website/music1.abc", "asciidoc/examples/website/music1.png", "asciidoc/examples/website/music-filter.html", "asciidoc/examples/website/layout1.conf", "asciidoc/examples/website/index.txt", "asciidoc/examples/website/build-website.sh", "asciidoc/examples/website/userguide.html",
      "asciidoc/examples/website/asciimath.html", "asciidoc/examples/website/layout1.css", "asciidoc/examples/website/music2.png", "asciidoc/examples/website/asciidoc-docbook-xsl.html", "asciidoc/examples/website/support.txt", "asciidoc/examples/website/latexmath.html", "asciidoc/examples/website/CHANGELOG.html", "asciidoc/examples/website/version9.html", "asciidoc/examples/website/music2.ly", "asciidoc/examples/website/manpage.html", "asciidoc/examples/website/latex-backend.html", "asciidoc/examples/website/downloads.html", "asciidoc/examples/website/README-website.txt", "asciidoc/BUGS", "asciidoc/asciidoc.py", "asciidoc/common.aap", "asciidoc/images/icons/up.png", "asciidoc/images/icons/warning.png", "asciidoc/images/icons/note.png", "asciidoc/images/icons/next.png", "asciidoc/images/icons/important.png", "asciidoc/images/icons/home.png", "asciidoc/images/icons/README", "asciidoc/images/icons/caution.png", "asciidoc/images/icons/tip.png", "asciidoc/images/icons/prev.png", "asciidoc/images/icons/callouts/10.png", "asciidoc/images/icons/callouts/12.png", "asciidoc/images/icons/callouts/3.png", "asciidoc/images/icons/callouts/2.png", "asciidoc/images/icons/callouts/5.png", "asciidoc/images/icons/callouts/7.png", "asciidoc/images/icons/callouts/8.png", "asciidoc/images/icons/callouts/11.png", "asciidoc/images/icons/callouts/9.png", "asciidoc/images/icons/callouts/1.png", "asciidoc/images/icons/callouts/4.png", "asciidoc/images/icons/callouts/6.png", "asciidoc/images/icons/callouts/13.png", "asciidoc/images/icons/callouts/15.png", "asciidoc/images/icons/callouts/14.png", "asciidoc/images/icons/example.png", "asciidoc/images/highlighter.png", "asciidoc/images/smallnew.png", "asciidoc/images/tiger.png", "asciidoc/CHANGELOG",
      "asciidoc/doc/asciidoc.1.html", "asciidoc/doc/source-highlight-filter.pdf", "asciidoc/doc/latexmath.txt", "asciidoc/doc/customers.csv", "asciidoc/doc/book.css-embedded.html", "asciidoc/doc/asciidoc.css.html", "asciidoc/doc/article.html", "asciidoc/doc/source-highlight-filter.html", "asciidoc/doc/book.txt", "asciidoc/doc/asciidoc.1", "asciidoc/doc/a2x.1", "asciidoc/doc/asciidoc.txt", "asciidoc/doc/asciidoc-revhistory.xml", "asciidoc/doc/article.txt", "asciidoc/doc/music-filter.html", "asciidoc/doc/asciidoc.dict", "asciidoc/doc/article.pdf", "asciidoc/doc/asciidoc.html", "asciidoc/doc/source-highlight-filter.txt", "asciidoc/doc/asciidoc.css-embedded.html", "asciidoc/doc/asciidoc.1.css.html", "asciidoc/doc/latex-backend.txt", "asciidoc/doc/article.css-embedded.html", "asciidoc/doc/music-filter.txt", "asciidoc/doc/asciimath.txt", "asciidoc/doc/book-multi.html", "asciidoc/doc/book-multi.txt", "asciidoc/doc/asciidoc.1.css-embedded.html", "asciidoc/doc/faq.txt", "asciidoc/doc/music-filter.pdf", "asciidoc/doc/main.aap", "asciidoc/doc/asciidoc.1.txt", "asciidoc/doc/latex-backend.html", "asciidoc/doc/asciidoc.conf", "asciidoc/doc/book-multi.css-embedded.html", "asciidoc/doc/book.html", "asciidoc/doc/a2x.1.txt", "asciidoc/INSTALL.txt", "asciidoc/javascripts/LaTeXMathML.js", "asciidoc/javascripts/toc.js", "asciidoc/javascripts/ASCIIMathML.js", "asciidoc/BUGS.txt",
      "asciidoc/text.conf", "asciidoc/CHANGELOG.txt", "asciidoc/xhtml-deprecated.conf", "asciidoc/INSTALL", "asciidoc/a2x", "asciidoc/README", "asciidoc/COPYING", "asciidoc/COPYRIGHT", "asciidoc/docbook-xsl/fo.xsl", "asciidoc/docbook-xsl/manpage.xsl", "asciidoc/docbook-xsl/asciidoc-docbook-xsl.txt", "asciidoc/docbook-xsl/chunked.xsl", "asciidoc/docbook-xsl/htmlhelp.xsl", "asciidoc/docbook-xsl/common.xsl", "asciidoc/docbook-xsl/shaded-literallayout.patch", "asciidoc/docbook-xsl/xhtml.xsl", "asciidoc/html4.conf", "asciidoc/dblatex/asciidoc-dblatex.xsl", "asciidoc/dblatex/asciidoc-dblatex.sty", "asciidoc/dblatex/dblatex-readme.txt", "asciidoc/linuxdoc.conf", "asciidoc/lang-es.conf", "asciidoc/install.sh", "asciidoc/xhtml11.conf", "asciidoc/README.txt", "asciidoc/t.conf", "asciidoc/xhtml11-quirks.conf", "asciidoc/docbook.conf", "asciidoc/math.conf", "asciidoc/asciidoc.conf", "asciidoc/latex.conf", "asciidoc/xhtml-deprecated-css.conf"
  ]
end
