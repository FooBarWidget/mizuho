desc "Run unit tests"
task :test do
	sh "spec -f s -c test/*_spec.rb"
end

desc "Build a gem"
task :gem do
	sh "gem build mizuho.gemspec"
end
