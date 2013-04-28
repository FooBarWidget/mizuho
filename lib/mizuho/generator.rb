# Copyright (c) 2008-2013 Hongli Lai
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

require 'nokogiri'
require 'mizuho'
require 'mizuho/source_highlight'
require 'mizuho/id_map'
require 'mizuho/utils'

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
		@attributes  = options[:attributes] || []
		@enable_topbar     = options[:topbar]
		@no_run            = options[:no_run]
		@commenting_system = options[:commenting_system]
		@index             = options[:index]
		@index_filename    = options[:index_filename] || default_index_filename(input)
		if @commenting_system == 'juvia'
			require_options(options, :juvia_url, :juvia_site_key)
		end
	end
	
	def start
		if @commenting_system
			@id_map = IdMap.new
			if File.exist?(@id_map_file)
				@id_map.load(@id_map_file)
			else
				warn "No ID map file, generating one (#{@id_map_file})..."
			end
		end
		if !@no_run
			self.class.run_asciidoc(@input_file, @output_file, @icons_dir,
				@conf_file, @attributes)
		end
		transform(@output_file)
		if @commenting_system
			@id_map.save(@id_map_file)
			stats = @id_map.stats
			if stats[:fuzzy] > 0
				warn "Warning: #{stats[:fuzzy]} fuzzy ID(s)"
			end
			if stats[:orphaned] > 0
				warn "Warning: #{stats[:orphaned]} unused ID(s)"
			end
		end
	end
	
	def self.run_asciidoc(input, output, icons_dir = nil, conf_file = nil, attributes = [])
		args = [
			ASCIIDOC,
			"-b", "html5",
			"-a", "theme=flask",
			"-a", "icons",
			"-n"
		].flatten
		if icons_dir
			args << "-a"
			args << "iconsdir=#{icons_dir}"
		end
		attributes.each do |attribute|
			args << "-a"
			args << attribute
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

	def default_index_filename(input)
		return File.dirname(input) +
			"/" +
			File.basename(input, File.extname(input)) +
			".index.sqlite3"
	end
	
	def warn(message)
		STDERR.puts(message)
	end
	
	def transform(filename)
		File.open(filename, 'r+') do |f|
			doc   = Nokogiri.HTML(f)
			head  = (doc / "head")[0]
			body  = (doc / "body")[0]
			title = (doc / "title")[0].text
			header_div = (doc / "#header")[0]
			headers    = (doc / "#content" / "h1, h2, h3, h4")
			
			head.add_child(make_node(stylesheet_tag, doc))

			# Remove footer with generation timestamp.
			(doc / "#footer-text").remove
			
			# Add commenting balloons.
			if @commenting_system
				titles = []
				headers.each do |header|
					if header['class'] !~ /float/
						titles << header.text
					end
				end
				@id_map.generate_associations(titles)
				headers.each do |header|
					if header['class'] !~ /float/
						titles << header.text
						header['data-comment-topic'] = @id_map.associations[header.text]
						header.add_previous_sibling(make_node(create_comment_balloon, doc))
					end
				end
			end
			
			# Add top bar.
			if @enable_topbar
				body.children.first.add_previous_sibling(make_node(topbar(title), doc))
			end

			# Add Mizuho Javascript.
			body.add_child(javascript_tag(doc))

			# Move preamble from content area to header area.
			if preamble = (doc / "#preamble")[0]
				preamble.remove
				header_div.add_child(make_node(preamble, doc))
			end
			
			# Create a TOC after the preamble.
			toc_div = add_child_and_get(header_div, %Q{<div id="toc"></div>})
			if @commenting_system
				# Add a commenting balloon to the TOC title.
				toc_div.add_child(make_node(create_comment_balloon, doc))
			end
			toc_div.add_child(make_node(%Q{<div id="toctitle">Table of Contents</div>}, doc))
			headers.each do |header|
				if header['class'] !~ /float/
					level = header.name.scan(/\d+/).first
					div  = add_child_and_get(toc_div, "<div class=\"foo toclevel#{level}\"></div>")
					link = add_child_and_get(div, "<a></a>")
					link['href'] = '#' + header['id']
					link.content = header.text
				end
			end

			if @enable_topbar
				# Add invisible spans before each header so that anchor jumps
				# don't hide the header behind the top bar.
				# http://nicolasgallagher.com/jump-links-and-viewport-positioning/
				headers.each do |header|
					span = add_previous_sibling_and_get(header, '<span class="anchor_helper"></span>')
					span['id'] = header['data-anchor'] = header['id']
					header.remove_attribute('id')
				end
			end

			if @index
				# Add docid attributes to headers.
				headers.each do |header|
					next if header['class'] =~ /float/
					docid = Utils.title_to_docid(header.text)
					header['data-docid'] = docid.to_s
					header['class'] = "#{header['class']} docid-#{docid}".strip
				end

				create_search_index(headers, @index_filename)
			end
			
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
	
	def topbar(title)
		content = render_template("topbar.html")
		content.gsub!(/\{TITLE\}/, title)
		return content
	end
	
	def javascript_tag(doc)
		node = Nokogiri::XML::Node.new('script', doc)
		content = ""
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
		node.content = content
		return node
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

	# For Nokogiri 1.4.0 compatibility
	def make_node(html, doc)
		result = Nokogiri::XML::Node.new('div', doc)
		result.inner_html = html
		return result.children[0]
	end

	# For Nokogiri 1.4.0 compatibility
	def add_child_and_get(node, html)
		result = node.add_child(make_node(html, node.document))
		result = result[0] if result.is_a?(Array)
		return result
	end

	# For Nokogiri 1.4.0 compatibility
	def add_previous_sibling_and_get(node, html)
		result = node.add_previous_sibling(make_node(html, node.document))
		result = result[0] if result.is_a?(Array)
		return result
	end

	def gather_content(header)
		result = []
		elem = header
		while true
			elem = elem.next_sibling
			if !elem || elem.name =~ /^h/i
				break
			else
				text = elem.text.strip
				if !text.empty?
					text.gsub!(/\r?\n/, " ")
					result << text
				end
			end
		end
		return result.join(" ")
	end

	def create_search_index(headers, filename)
		require 'sqlite3'
		db = SQLite3::Database.new("#{filename}.tmp")
		db.transaction do
			db.execute(%q{
				CREATE VIRTUAL TABLE book USING fts4(
					title TEXT NOT NULL,
					content TEXT NOT NULL,
					content="",
					tokenize=porter
				)
			})
			db.execute(%q{
				CREATE TABLE version(
					version INTEGER NOT NULL
				)
			})
			db.execute("INSERT INTO version VALUES(1)")
			db.prepare("INSERT INTO book(docid, title, content) VALUES(?, ?, ?)") do |stmt|
				headers.each do |header|
					next if header['class'] =~ /float/
					title = header.text.strip
					docid = Utils.title_to_docid(title)
					content = gather_content(header)
					stmt.execute(docid, title, content)
				end
			end
		end
		db.execute("INSERT INTO book(book) VALUES('optimize')")
		db.execute("VACUUM")
		db.close
		File.rename("#{filename}.tmp", filename)
	rescue Exception => e
		File.unlink("#{filename}.tmp") rescue nil
		raise e
	end
end

end
