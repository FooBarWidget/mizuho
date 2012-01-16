require 'nokogiri'
require 'mizuho'
require 'mizuho/source_highlight'
require 'mizuho/id_map'

module Mizuho

class GenerationError < StandardError
end

class Generator
	def initialize(input, options = {})
		@options     = options
		@input_file  = input
		@output_file = options[:output] || default_output_filename(input)
		@id_map_file = options[:id_map] || default_id_map_filename(input)
		@icons_dir   = options[:icons_dir]
		@conf_file   = options[:conf_file]
		@enable_topbar     = options[:topbar]
		@commenting_system = options[:commenting_system]
		if @commenting_system == 'juvia'
			require_options(options, :juvia_url, :juvia_site_key)
		end
	end
	
	def start
		if @commenting_system
			@id_map = IdMap.new(@input_file)
			if File.exist?(@id_map_file)
				@id_map.load(@id_map_file)
			else
				warn "No ID map file, generating one (#{@id_map_file})..."
			end
		end
		self.class.run_asciidoc(@input_file, @output_file, @icons_dir, @conf_file)
		transform(@output_file)
		if @commenting_system
			@id_map.save(@id_map_file)
			if @id_map.fuzzy_count > 0
				warn "Warning: #{@id_map.fuzzy_count} fuzzy ID(s)"
			end
			if @id_map.orphaned_count > 0
				warn "Warning: #{@id_map.orphaned_count} orphaned ID(s)"
			end
		end
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
	
	def warn(message)
		STDERR.puts(message)
	end
	
	def transform(filename)
		File.open(filename, 'r+') do |f|
			doc = Nokogiri.HTML(f)
			head = (doc / "head")[0]
			body = (doc / "body")[0]
			preamble = (doc / "#preamble")[0]
			toctitle = (doc / "#toctitle")[0]
			
			head.add_child(stylesheet_tag)
			
			if @commenting_system
				headers = (doc / "#content h2, #content h3, #content h4")
				headers.each do |header|
					header['data-comment-topic'] = @id_map.associate(header.text)
					header.add_previous_sibling(create_comment_balloon)
				end
			end
			
			if @enable_topbar
				body.children.first.add_previous_sibling(topbar)
			end
			body.add_child(javascript_tag)
			
			if preamble
				preamble.remove
				preamble_copy = (doc / "#header > h1")[0].add_next_sibling(preamble.to_s)[0]
				preamble_copy['id'] = 'preamble'
			end
			
			toctitle.add_previous_sibling(create_comment_balloon)
			
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
		content << css << "\n"
		
		if @enable_topbar
			content << File.read("#{TEMPLATES_DIR}/topbar.css") << "\n"
		end
		
		if @commenting_system == 'disqus'
			content << File.read("#{TEMPLATES_DIR}/disqus.css") << "\n"
		elsif @commenting_system == 'intensedebate'
			content << File.read("#{TEMPLATES_DIR}/intensedebate.css") << "\n"
		end
		
		content << %Q{</style>\n}
		return content
	end
	
	def topbar
		return render_template("topbar.html")
	end
	
	def javascript_tag
		content = %Q{<script>}
		content << File.read("#{TEMPLATES_DIR}/jquery-1.7.1.min.js") << "\n"
		content << File.read("#{TEMPLATES_DIR}/jquery.hashchange-1.0.0.js") << "\n"
		content << File.read("#{TEMPLATES_DIR}/mizuho.js") << "\n"
		if @enable_topbar
			content << File.read("#{TEMPLATES_DIR}/topbar.js") << "\n"
		end
		if @commenting_system == 'juvia'
			content << %Q{
				var JUVIA_URL = '#{@options[:juvia_url]}';
				var JUVIA_SITE_KEY = '#{@options[:juvia_site_key]}';
			}
			content << File.read("#{TEMPLATES_DIR}/juvia.js") << "\n"
		end
		content << %Q{</script>}
		return content
	end
	
	def create_comment_balloon
		return %Q{<a href="javascript:void(0)" class="comments empty" title="Add a comment"><span class="count"></span></a>}
	end
	
	def render_template(name)
		content = File.read("#{TEMPLATES_DIR}/#{name}")
		content.gsub!(/\{INLINE_IMAGE:(.*?)\.png\}/) do
			data = File.open("#{TEMPLATES_DIR}/#{$1}.png", "rb") do |f|
				f.read
			end
			data = [data].pack('m')
			data.gsub!("\n", "")
			"data:image/png;base64,#{data}"
		end
		return content
	end

	def require_options(options, *required_keys)
		fail = false
		required_keys.each do |key|
			if !options.has_key?(key)
				fail = true
				argument_name = '--' + key.to_s.gsub('_', '-')
				STDERR.puts "You must also specify #{argument_name}!"
			end
		end
		exit 1 if fail
	end
end

end
