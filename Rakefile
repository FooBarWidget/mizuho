$LOAD_PATH.unshift(File.expand_path(File.dirname(__FILE__) + "/lib"))
require 'mizuho'

def string_option(name, default_value = nil)
	value = ENV[name]
	if value.nil? || value.empty?
		return default_value
	else
		return value
	end
end

def recursive_copy_files(files, destination_dir)
	files.each_with_index do |filename, i|
		dir = File.dirname(filename)
		if !File.exist?("#{destination_dir}/#{dir}")
			FileUtils.mkdir_p("#{destination_dir}/#{dir}")
		end
		if !File.directory?(filename)
			FileUtils.install(filename, "#{destination_dir}/#{filename}")
		end
		printf "\r[%5d/%5d] [%3.0f%%] Copying files...", i + 1, files.size, i * 100.0 / files.size
		STDOUT.flush
	end
end

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
	require 'fileutils'
	require 'mizuho/packaging'

	basename = "mizuho_#{Mizuho::VERSION_STRING}~hongli"
	sh "rm -rf pkg/#{basename}"
	sh "mkdir -p pkg/#{basename}"
	recursive_copy_files(Dir[*MIZUHO_FILES] - Dir[*MIZUHO_DEBIAN_EXCLUDE_FILES],
		"pkg/#{basename}")
	puts

	sh "cd pkg && tar -c #{basename} | gzip --best > #{basename}.orig.tar.gz"

	recursive_copy_files(Dir["debian/**/*"], "pkg/#{basename}")
	puts
	sh "cd pkg/#{basename} && dpkg-buildpackage -us -uc"
end
