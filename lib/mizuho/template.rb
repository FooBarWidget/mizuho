require 'erb'
require 'cgi'
require 'mizuho/heading'

module Mizuho

class Template
	def initialize(input, template_file)
		@input = input
		@template_file = template_file
		@base_dir = File.expand_path(File.dirname(@template_file))
	end
	
	def apply
		# Extract the title, and get rid of asciidoc's default layout.
		@contents = File.read(@input)
		@contents =~ %r{<title>(.*?)</title>}
		@title = CGI::unescapeHTML($1)
		@contents.sub!(/\A.*?(<div id="preamble">)/m, '\1')
		@contents.sub!(/<div id="footer">.*/m, '')
		
		@table_of_contents = parse_table_of_contents(@contents)
		
		# Apply our own template on the "naked" contents.
		erb = ERB.new(File.read(@template_file), nil, '-')
		@output_contents = eval(erb.src, get_binding, @template_file)
	end
	
	def save(output_file)
		File.open(output_file, 'w') do |f|
			f.write(@output_contents)
		end
	end

protected
	include ERB::Util
	attr_reader :title
	attr_reader :contents
	attr_accessor :table_of_contents
	
	def include_file(basename)
		return File.read(File.join(@base_dir, basename))
	end
	
private
	def get_binding
		return binding
	end
	
	def parse_table_of_contents(html)
		current_heading = toplevel_heading = Heading.new
		current_heading.title = @title
		current_heading.level = 1
		offset = 0
		while true
			offset = html.index(%r{<h(\d) id="(.*?)">(.*?)</h\d>}, offset)
			break if offset.nil?
			offset = $~.end(0)
			level = $1.to_i
			anchor = CGI::unescapeHTML($2)
			title = CGI::unescapeHTML($3)
			
			new_heading = Heading.new
			new_heading.title = title
			new_heading.level = level
			new_heading.anchor = anchor
			new_heading.parent = current_heading.find_parent_with_level(level - 1)
			new_heading.parent.children << new_heading
			current_heading = new_heading
		end
		return toplevel_heading.children
	end
end

end
