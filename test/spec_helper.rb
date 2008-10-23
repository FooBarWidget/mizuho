$LOAD_PATH << File.expand_path(File.dirname(__FILE__) + "/../lib")
require 'digest/md5'
require 'mizuho/generator'

CACHE_DIR = File.expand_path(File.dirname(__FILE__) + "/cache")

def generate_and_parse(text)
	Dir.mkdir(CACHE_DIR) if !File.exist?(CACHE_DIR)
	
	# Unindent text.
	lines = text.split(/\r?\n/)
	min_indenting = nil
	lines.each do |line|
		next if line.strip.empty?
		line =~ /\A([\t\s]*)/
		if min_indenting.nil? || $1.size < min_indenting
			min_indenting = $1.size
		end
	end
	if min_indenting
		lines.map! do |line|
			line[min_indenting..-1]
		end
	end
	text = lines.join("\n")
	
	output_filename = File.join(CACHE_DIR, Digest::MD5.hexdigest(text)) + ".html"
	
	# Generate Asciidoc output if it isn't cached, otherwise use cached version.
	if !File.exist?(output_filename)
		input_filename = File.join(CACHE_DIR, "input.#{Process.pid}.txt")
		begin
			File.open(input_filename, 'w') do |f|
				f.write(text)
			end
			Mizuho::Generator.run_asciidoc(input_filename, output_filename)
		ensure
			File.unlink(input_filename) rescue nil
		end
	end
	
	return Mizuho::Parser.new(output_filename)
end
