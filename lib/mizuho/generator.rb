require 'optparse'
require 'mizuho/parser'
require 'mizuho/template'

module Mizuho

class GenerationError < StandardError
end

class Generator
	def initialize(input, output = nil, template = nil, multi_page = false)
		@input = input
		if output
			@output_name = output
		else
			@output_name = File.expand_path(input.sub(/(.*)\..*$/, '\1'))
		end
		@template = template
		@multi_page = multi_page
	end
	
	def start
		run_asciidoc(@input, "#{@output_name}.html")
		if @template
			apply_template("#{@output_name}.html", @template, @multi_page)
		end
	end

private
	ASCIIDOC = File.expand_path(File.dirname(__FILE__) + "/../../asciidoc/asciidoc.py")

	def run_asciidoc(input, output)
		if !system("python", ASCIIDOC, "-a", "toc", "-n", "-o", output, input)
			raise GenerationError, "Asciidoc failed."
		end
	end
	
	def apply_template(asciidoc_file, template_file, multi_page)
		parser = Parser.new(asciidoc_file)
		if multi_page
			File.unlink(asciidoc_file)
			puts "TODO"
		else
			template = Template.new(template_file,
				:title => parser.title,
				:table_of_contents => parser.table_of_contents,
				:contents => parser.contents)
			template.save(asciidoc_file)
		end
	end
end

end
