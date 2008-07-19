require 'erb'
require 'cgi'

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
		
		# Apply our own template on the "naked" contents.
		erb = ERB.new(File.read(@template_file), nil, '')
		@output_contents = erb.result(get_binding)
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
	
	def include_file(basename)
		return File.read(File.join(@base_dir, basename))
	end
	
	def get_binding
		return binding
	end
end

end
