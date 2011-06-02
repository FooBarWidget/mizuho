require 'nokogiri'
require 'mizuho'
require 'mizuho/source_highlight'
require 'mizuho/id_map'

module Mizuho

class GenerationError < StandardError
end

class Generator
	def initialize(input, options = {})
		@input_file  = input
		@output_file = options[:output] || default_output_filename(input)
		@id_map_file = options[:id_map] || default_id_map_filename(input)
		@icons_dir   = options[:icons_dir]
		@conf_file   = options[:conf_file]
	end
	
	def start
		@id_map = IdMap.new
		@id_map.load(@id_map_file)
		#self.class.run_asciidoc(@input_file, @output_file, @icons_dir, @conf_file)
		transform(@output_file)
		@id_map.save(@id_map_file)
	end
	
	def self.run_asciidoc(input, output, icons_dir = nil, conf_file = nil)
		args = [
			"python", ASCIIDOC,
			"-b", "html5",
			"-a", "toc",
			"-a", "theme=flask",
			"-a", "toclevels=3",
			"-a", "icons",
			"-n"
		]
		if icons_dir
			args << "-a"
			args << "iconsdir=#{icons_dir}"
		end
		if conf_file
			# With the splat operator we support a string and an array of strings.
			[*conf_file].each do |cf|
				args << "-f"
				args << cf
			end
		end
		args += ["-o", output, input]
		if !system(*args)
			raise GenerationError, "Asciidoc failed."
		end
	end

private
	def default_output_filename(input)
		return File.dirname(input) +
			"/" +
			File.basename(input, File.extname(input)) +
			".html"
	end
	
	def default_id_map_filename(input)
		return File.dirname(input) +
			"/" +
			File.basename(input, File.extname(input)) +
			".idmap.txt"
	end
	
	def transform(filename)
		File.open(filename, 'r+') do |f|
			doc = Nokogiri.HTML(f)
			head = (doc / "head")[0]
			body = (doc / "body")[0]
			
			head.add_child(stylesheet_tag)
			
			headers = (doc / "#content h2, #content h3")
			headers.each do |header|
				header['data-comment-topic'] = @id_map.associate(header.text)
				header.add_previous_sibling(comment_container)
			end
			
			body.add_child(javascript_tag)
			
			f.rewind
			f.truncate(0)
			f.puts(doc.to_html)
		end
	end
	
	def stylesheet_tag
		content = %Q{<style type="text/css">\n}
		css = File.read("#{TEMPLATES_DIR}/mizuho.css")
		css.gsub!(/url\('(.*?)\.png'\)/) do
			data = File.open("#{TEMPLATES_DIR}/#{$1}.png", "rb") do |f|
				f.read
			end
			data = [data].pack('m')
			data.gsub!("\n", "")
			"url('data:image/png;base64,#{data}')"
		end
		content << css
		content << %Q{</style>\n}
		return content
	end
	
	def javascript_tag
		content = %Q{<script>}
		content << File.read("#{TEMPLATES_DIR}/jquery-1.6.1.min.js")
		content << File.read("#{TEMPLATES_DIR}/mizuho.js")
		content << %Q{</script>}
		return content
	end
	
	def comment_container
		return %Q{<a href="javascript:void(0)" class="comments empty" title="Add a comment"><span class="count"></span></a>}
	end
end

end
