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
			determine_chapter_and_heading_filenames(parser.chapters)
			parser.chapters.each do |chapter|
				template = Template.new(template_file,
					:multi_page? => true,
					:title => parser.title,
					:table_of_contents => parser.table_of_contents,
					:contents => chapter.contents,
					:is_preamble? => chapter.heading.nil?,
					:preamble_anchor => parser.chapters.first.filename,
					:chapter_title => chapter.title,
					:chapter_title_without_numbers => chapter.title_without_numbers)
				template.save(chapter.filename)
			end
		else
			template = Template.new(template_file,
				:multi_page? => false,
				:title => parser.title,
				:table_of_contents => parser.table_of_contents,
				:contents => parser.contents)
			template.save(asciidoc_file)
		end
	end
	
	def determine_chapter_and_heading_filenames(chapters)
		chapters.each_with_index do |chapter, i|
			if chapter.is_preamble?
				chapter.filename = File.basename("#{@output_name}.html")
			else
				chapter.filename = sprintf("%s-%02d.html", @output_name, i)
				chapter.heading.filename = File.basename(chapter.filename)
				chapter.heading.each_descendant do |h|
					h.filename = File.basename(chapter.filename)
				end
			end
		end
	end
end

end
