require 'optparse'
require 'mizuho/parser'
require 'mizuho/template'

module Mizuho

class GenerationError < StandardError
end

class Generator
	def initialize(input, output = nil, template = nil)
		@input = input
		if output
			@output = output
		else
			@output = File.expand_path(input.sub(/(.*)\..*$/, '\1.html'))
		end
		@template = template
	end
	
	def start
		run_asciidoc(@input, @output)
		apply_template(@output, @template) if @template
	end

private
	ASCIIDOC = File.expand_path(File.dirname(__FILE__) + "/../../asciidoc/asciidoc.py")

	def run_asciidoc(input, output)
		if !system("python", ASCIIDOC, "-a", "toc", "-n", "-o", output, input)
			raise GenerationError, "Asciidoc failed."
		end
	end
	
	def apply_template(file, template_file)
		parser = Parser.new(file)
		template = Template.new(template_file,
			:title => parser.title,
			:table_of_contents => parser.table_of_contents,
			:contents => parser.contents)
		template.save(file)
	end
end

end
