require File.expand_path('lib/mizuho')
require File.expand_path('lib/mizuho/packaging')

Gem::Specification.new do |s|
	s.name = "mizuho"
	s.version = Mizuho::VERSION_STRING
	s.summary = "Mizuho documentation formatting tool"
	s.email = "hongli@phusion.nl"
	s.homepage = "https://github.com/FooBarWidget/mizuho"
	s.description = "A documentation formatting tool. Mizuho converts Asciidoc input files into nicely outputted HTML, possibly one file per chapter. Multiple templates are supported, so you can write your own."
	s.executables = ["mizuho", "mizuho-asciidoc"]
	s.authors = ["Hongli Lai"]
	s.add_dependency("nokogiri", ">= 1.4.0")
	s.add_dependency("sqlite3")
	s.files = Dir[*MIZUHO_FILES]
end
