desc "Run unit tests"
task :test do
	ruby "-S spec -f s -c test/*_spec.rb"
end

desc "Build a gem"
task :gem do
	ruby "-S gem build mizuho.gemspec"
end

desc "Build a gem and install it"
task :install => :gem do
	File.read("mizuho.gemspec") =~ /s\.version = \"(.*?)\"/
	version = $1
	ruby "-S gem install mizuho-#{version}.gem"
end

desc "Generate an Asciidoc file list, suitable for pasting into the gemspec"
task :generate_asciidoc_file_list do
	puts Dir["asciidoc/**/*"].inspect
end

task :generate_source_highlight_file_list do
	puts Dir["source-highlight/**/*"].inspect
end