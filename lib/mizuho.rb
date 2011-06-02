module Mizuho
	SOURCE_ROOT   = File.expand_path(File.dirname(__FILE__) + "/..")
	LIBDIR        = "#{SOURCE_ROOT}/lib"
	TEMPLATES_DIR = "#{SOURCE_ROOT}/templates"
	ASCIIDOC      = "#{SOURCE_ROOT}/asciidoc/asciidoc.py"
	
	VERSION_STRING = "0.9.8"
	
	if $LOAD_PATH.first != LIBDIR
		$LOAD_PATH.unshift(LIBDIR)
		$LOAD_PATH.uniq!
	end
end if !defined?(Mizuho::SOURCE_ROOT)