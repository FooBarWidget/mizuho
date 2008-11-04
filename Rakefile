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
