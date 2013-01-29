# Copyright (c) 2013 Hongli Lai
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

module Mizuho

module Utils
	extend self

	def self.included(klass)
		# When included into another class, make sure that Utils
		# methods are made private.
		public_instance_methods(false).each do |method_name|
			klass.send(:private, method_name)
		end
	end

	# Given a title with a chapter number, e.g. "6.1 Installation using tarball",
	# splits the two up.
	def extract_chapter(title)
		title =~ /^((\d+\.)*) (.+)$/
		chapter = $1
		pure_title = $3
		if !chapter.nil? && !chapter.empty? && pure_title && !pure_title.empty?
			return [chapter, pure_title]
		else
			return nil
		end
	end

	def chapter_to_int_array(chapter)
		return chapter.split('.').map { |x| x.to_i }
	end

	def title_to_docid(title)
		chapter, pure_title = extract_chapter(title)
		p title
		numbers = chapter_to_int_array(chapter)
		result = 0
		bit_offset = 0
		numbers.each do |num|
			result = result | (num << bit_offset)
			bit_offset += 5
		end
		return result
	end
end

end
