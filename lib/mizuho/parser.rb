require 'cgi'
require 'mizuho/heading'

module Mizuho

class Chapter
	attr_accessor :title
	attr_accessor :contents
end

# This class can parse the raw Asciidoc XHTML output, and extract the title, raw
# contents (without layout) and other information from it.
class Parser
	attr_reader :title
	attr_reader :table_of_contents
	attr_reader :contents

	def initialize(filename)
		@contents = File.read(filename)
		
		# Extract the title.
		@contents =~ %r{<title>(.*?)</title>}
		@title = CGI::unescapeHTML($1)
		
		# Get rid of the Asciidoc layout and unwanted elements.
		@contents.sub!(/\A.*?(<div id="preamble">)/m, '\1')
		@contents.sub!(/<div id="footer">.*/m, '')
		@contents.gsub!(%r{<div style="clear:left"></div>}, '')
		
		# Extract table of contents.
		@table_of_contents = parse_table_of_contents(@contents)
	end
	
	def chapers
		@@chapters ||= parse_chapters(@contents)
	end

private
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
	
	def parse_chapters(html)
		# TODO
		return []
	end
end

end
