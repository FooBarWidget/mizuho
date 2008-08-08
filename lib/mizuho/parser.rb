require 'cgi'
require 'mizuho/heading'
require 'mizuho/chapter'

module Mizuho

# This class can parse the raw Asciidoc XHTML output, and extract the title, raw
# contents (without layout) and other information from it.
class Parser
	# The document's title.
	attr_reader :title
	# The document's table of contents, represented in a tree structure
	# by Heading objects.
	attr_reader :table_of_contents
	# The document's raw contents, without any layout.
	attr_reader :contents

	# Parse the given file.
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
		parse_table_of_contents(@contents)
	end
	
	# Returns the individual chapters as an array of Chapter objects. The
	# first Chapter object represents the preamble.
	def chapters
		@@chapters ||= parse_chapters(@contents)
	end

private
	def parse_table_of_contents(html)
		@headings = []
		current_heading = toplevel_heading = Heading.new
		current_heading.title = @title
		current_heading.level = 1
		offset = 0
		while true
			offset = html.index(%r{<h(\d) id="(.*?)">(.*?)</h\d>}, offset)
			break if offset.nil?
			offset = $~.end(0)
			level  = $1.to_i
			anchor = CGI::unescapeHTML($2)
			title  = $3
			
			new_heading = Heading.new
			new_heading.title = title
			new_heading.level = level
			new_heading.anchor = "##{anchor}"
			new_heading.parent = current_heading.find_parent_with_level(level - 1)
			new_heading.parent.children << new_heading
			current_heading = new_heading
			@headings << new_heading
		end
		@table_of_contents = toplevel_heading.children
	end
	
	def parse_chapters(html)
		if !defined?(Hpricot)
			require 'rubygems'
			require 'hpricot'
		end
		doc = Hpricot(contents)
		result = []
		# TODO: fix cross-references
		(doc / 'div.sectionbody').each_with_index do |elem, i|
			chapter = Chapter.new
			if i > 0
				chapter.heading = @table_of_contents[i - 1]
			end
			chapter.contents = elem.inner_html
			result << chapter
		end
		return result
	end
end

end
