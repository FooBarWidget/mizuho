require 'rake/gempackagetask'

desc "Run unit tests"
task :test do
	ruby "-S spec -f s -c test/*_spec.rb"
end

desc "Build a gem and install it"
task :install => :gem do
	File.read("mizuho.gemspec") =~ /s\.version = \"(.*?)\"/
	version = $1
	ruby "-S gem install mizuho-#{version}.gem"
end

spec = Gem::Specification.new do |s|
	s.name = "mizuho"
	s.version = "0.9.6"
	s.summary = "Mizuho documentation formatting tool"
	s.email = "hongli@phusion.nl"
	s.homepage = "http://github.com/FooBarWidget/mizuho/tree/master"
	s.description = "A documentation formatting tool. Mizuho converts Asciidoc input files into nicely outputted HTML, possibly one file per chapter. Multiple templates are supported, so you can write your own."
	s.has_rdoc = false
	s.executables = ["mizuho", "mizuho-asciidoc"]
	s.authors = ["Hongli Lai"]
	s.add_dependency("hpricot")
	
	s.files = FileList[
		"README.markdown", "LICENSE.txt", "Rakefile",
		"bin/*",
		"lib/**/*",
		"test/*",
		"templates/*",
		"asciidoc/**/*",
		"source-highlight/**/*"
	]
end

Rake::GemPackageTask.new(spec) do |pkg|
	pkg.need_zip = false
	pkg.need_tar = false
end