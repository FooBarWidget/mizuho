require 'cgi'

module Mizuho

class Heading
	# The heading title, as HTML. Non-HTML special characters are already escaped.
	attr_accessor :title
	attr_accessor :level
	attr_accessor :basename
	attr_accessor :anchor
	attr_accessor :parent
	attr_accessor :children
	
	def initialize
		@children = []
	end
	
	def find_parent_with_level(level)
		h = self
		while h && h.level != level
			h = h.parent
		end
		return h
	end
	
	# The heading title without section number, as HTML. Non-HTML special characters
	# are already escaped.
	def title_without_numbers
		return title.sub(/^(\d+\.)+ /, '')
	end
	
	# The heading title without section number, as plain text. Contains no HTML
	# elements. Non-HTML special characters are not escaped.
	def plain_title
		return CGI::unescapeHTML(title_without_numbers.gsub(%r{</?[a-z]+>}i, ''))
	end
	
	def each_descendant(&block)
		children.each do |h|
			block.call(h)
			h.each_descendant(&block)
		end
	end
end

end
