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

module Mizuho
	VERSION_STRING    = "0.9.19"
	NATIVELY_PACKAGED = false

	if NATIVELY_PACKAGED
		TEMPLATES_DIR    = "/usr/share/mizuho/templates"
		if File.exist?("/usr/share/mizuho/asciidoc")
			ASCIIDOC = ["/usr/bin/python", "/usr/share/mizuho/asciidoc/asciidoc.py"]
		else
			ASCIIDOC = "/usr/bin/asciidoc"
		end
	else
		SOURCE_ROOT   = File.expand_path(File.dirname(__FILE__) + "/..")
		LIBDIR        = "#{SOURCE_ROOT}/lib"
		
		TEMPLATES_DIR = "#{SOURCE_ROOT}/templates"
		ASCIIDOC      = ["python", "#{SOURCE_ROOT}/asciidoc/asciidoc.py"]

		if $LOAD_PATH.first != LIBDIR
			$LOAD_PATH.unshift(LIBDIR)
			$LOAD_PATH.uniq!
		end
	end
end if !defined?(Mizuho::VERSION_STRING)
