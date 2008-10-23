require 'optparse'
require 'digest/sha1'
require 'mizuho/parser'
require 'mizuho/template'

module Mizuho

class GenerationError < StandardError
end

class Generator
	def initialize(input, output = nil, template_name = nil, multi_page = false, icons_dir = nil)
		@input = input
		if output
			@output_name = output
		else
			@output_name = File.expand_path(input.sub(/(.*)\..*$/, '\1'))
		end
		@template = locate_template_file(template_name)
		@multi_page = multi_page
		@icons_dir = icons_dir
	end
	
	def start
		self.class.run_asciidoc(@input, "#{@output_name}.html", @icons_dir)
		if @template
			apply_template("#{@output_name}.html", @template, @multi_page)
		end
	end
	
	def self.run_asciidoc(input, output, icons_dir = nil)
		args = ["python", ASCIIDOC, "-a", "toc", "-a", "icons"]
		if icons_dir
			args << "-a"
			args << "iconsdir=#{icons_dir}"
		end
		args += ["-n", "-o", output, input]
		if !system(*args)
			raise GenerationError, "Asciidoc failed."
		end
	end

private
	ROOT = File.expand_path(File.dirname(__FILE__) + "/../..")
	ASCIIDOC = "#{ROOT}/asciidoc/asciidoc.py"

	def locate_template_file(template_name)
		if template_name.nil?
			return "#{ROOT}/templates/asciidoc.html.erb"
		elsif template_name =~ %r{[/.]}
			# Looks like a filename.
			return template_name
		else
			return "#{ROOT}/templates/#{template_name}.html.erb"
		end
	end
	
	def apply_template(asciidoc_file, template_file, multi_page)
		parser = Parser.new(asciidoc_file)
		if multi_page
			File.unlink(asciidoc_file)
			assign_chapter_filenames_and_heading_basenames(parser.chapters)
			parser.chapters.each_with_index do |chapter, i|
				template = Template.new(template_file,
					:multi_page? => true,
					:title => parser.title,
					:table_of_contents => parser.table_of_contents,
					:contents => chapter.contents,
					:is_preamble? => chapter.heading.nil?,
					:chapters => parser.chapters,
					:prev_chapter => (i <= 1) ? nil : parser.chapters[i - 1],
					:current_chapter => chapter,
					:next_chapter => parser.chapters[i + 1])
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
	rescue Template::Error => e
		STDERR.puts("*** #{template_file}:\n#{e}")
		exit 1
	end
	
	def assign_chapter_filenames_and_heading_basenames(chapters)
		chapters.each_with_index do |chapter, i|
			if chapter.is_preamble?
				chapter.filename = "#{@output_name}.html"
			else
				title_sha1 = Digest::SHA1.hexdigest(chapter.title_without_numbers)
				chapter.filename = sprintf("%s-%s.html", @output_name,
					title_sha1.slice(0..7))
				chapter.heading.basename = File.basename(chapter.filename)
				chapter.heading.each_descendant do |h|
					h.basename = File.basename(chapter.filename)
				end
			end
		end
	end
end

end
