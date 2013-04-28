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

def boolean_option(name, default_value = false)
	value = ENV[name]
	if value.nil? || value.empty?
		return default_value
	else
		return value == "yes" || value == "on" || value == "true" || value == "1"
	end
end

def recursive_copy_files(files, destination_dir)
	require 'fileutils' if !defined?(FileUtils)
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
	printf "\r[%5d/%5d] [%3.0f%%] Copying files...\n", files.size, files.size, 100
end

def create_debian_package_dir(distribution)
	require 'mizuho/packaging'
	require 'time'

	sh "rm -rf #{PKG_DIR}/#{distribution}"
	sh "mkdir -p #{PKG_DIR}/#{distribution}"
	recursive_copy_files(Dir[*MIZUHO_FILES] - Dir[*MIZUHO_DEBIAN_EXCLUDE_FILES],
		"#{PKG_DIR}/#{distribution}")
	recursive_copy_files(Dir["debian/**/*"], "#{PKG_DIR}/#{distribution}")
	changelog = File.read("#{PKG_DIR}/#{distribution}/debian/changelog")
	changelog =
		"mizuho (#{Mizuho::VERSION_STRING}-1~#{distribution}1) #{distribution}; urgency=low\n" +
		"\n" +
		"  * Package built.\n" +
		"\n" +
		" -- Hongli Lai <hongli@phusion.nl>  #{Time.now.rfc2822}\n\n" +
		changelog
	File.open("#{PKG_DIR}/#{distribution}/debian/changelog", "w") do |f|
		f.write(changelog)
	end
end

PKG_DIR  = string_option('PKG_DIR', "pkg")
BASENAME = "mizuho_#{Mizuho::VERSION_STRING}"
DISTRIBUTIONS = ["raring", "precise", "lucid"]


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

# Dev
#   remake tarball
#   make package
# Production
#   use existing tarball or make new
#   make package

task 'package:debian:orig_tarball' do
	if File.exist?("#{PKG_DIR}/mizuho_#{Mizuho::VERSION_STRING}.orig.tar.gz")
		puts "Debian orig tarball #{PKG_DIR}/mizuho_#{Mizuho::VERSION_STRING}.orig.tar.gz already exists."
	else
		require 'mizuho/packaging'

		sh "rm -rf #{PKG_DIR}/#{BASENAME}"
		sh "mkdir -p #{PKG_DIR}/#{BASENAME}"
		recursive_copy_files(Dir[*MIZUHO_FILES] - Dir[*MIZUHO_DEBIAN_EXCLUDE_FILES],
			"#{PKG_DIR}/#{BASENAME}")
		sh "cd #{PKG_DIR} && tar -c #{BASENAME} | gzip --best > #{BASENAME}.orig.tar.gz"
	end
end

desc "Build a Debian package for local testing"
task 'package:debian:dev' do
	sh "dpkg-checkbuilddeps"
	sh "rm -f #{PKG_DIR}/mizuho_#{Mizuho::VERSION_STRING}.orig.tar.gz"
	Rake::Task["package:debian:clean"].invoke
	Rake::Task["package:debian:orig_tarball"].invoke
	create_debian_package_dir("dev")
	sh "cd #{PKG_DIR}/dev && debuild -us -uc"
end

desc "Build Debian multiple source packages to be uploaded to repositories"
task 'package:debian:production' => 'package:debian:orig_tarball' do
	sh "dpkg-checkbuilddeps"
	DISTRIBUTIONS.each do |distribution|
		create_debian_package_dir(distribution)
		sh "cd #{PKG_DIR}/#{distribution} && debuild -S -k0x0A212A8C"
	end
end

desc "Clean Debian packaging products, except for orig tarball"
task 'package:debian:clean' do
	files = Dir["#{PKG_DIR}/*.{changes,build,deb,dsc,upload}"]
	sh "rm -f #{files.join(' ')}"
	sh "rm -rf #{PKG_DIR}/dev"
	DISTRIBUTIONS.each do |distribution|
		sh "rm -rf #{PKG_DIR}/#{distribution}"
	end
	sh "rm -rf #{PKG_DIR}/*.debian.tar.gz"
end
