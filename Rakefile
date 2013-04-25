$LOAD_PATH.unshift(File.expand_path(File.dirname(__FILE__) + "/lib"))
require 'mizuho'

desc "Run unit tests"
task :test do
	ruby "-S spec -f s -c test/*_spec.rb"
end

desc "Build, sign & upload gem"
task 'package:release' do
	sh "git tag -s release-#{Mizuho::VERSION_STRING}"
	sh "gem build mizuho.gemspec --sign --key 0x0A212A8C"
	puts "Proceed with pushing tag to Github and uploading the gem? [y/n]"
	if STDIN.readline == "y\n"
		sh "git push origin release-#{Mizuho::VERSION_STRING}"
		sh "gem push mizuho-#{Mizuho::VERSION_STRING}.gem"
	else
		puts "Did not upload the gem."
	end
end

desc "Build Debian package"
task 'package:debian' do
	sh "dpkg-buildpackage -us -uc"
end
