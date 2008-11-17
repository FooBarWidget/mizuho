require 'optparse'
require 'digest/sha1'
require 'mizuho/parser'
require 'mizuho/template'

module Mizuho

class GenerationError < StandardError
end

class Generator
	def initialize(input, options = {})
		@input_file = input
		@output_name = options[:output]
		@template = locate_template_file(options[:template])
		@multi_page = options[:multi_page]
		@icons_dir = options[:icons_dir]
		@conf_file = options[:conf_file]
	end
	
	def start
		output_filename = determine_output_filename(@input_file, @output_name)
		self.class.run_asciidoc(@input_file, output_filename, @icons_dir, @conf_file)
		if @template
			apply_template(output_filename, @input_file, @output_name, @template, @multi_page)
		end
	end
	
	def self.run_asciidoc(input, output, icons_dir = nil, conf_file = nil)
		args = ["python", ASCIIDOC, "-a", "toc", "-a", "icons"]
		if icons_dir
			args << "-a"
			args << "iconsdir=#{icons_dir}"
		end
		if conf_file
			# With the splat operator we support a string and an array of strings.
			[*conf_file].each do |cf|
				args << "-f"
				args << cf
			end
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
	
	def determine_output_filename(input, output = nil, chapter_id = nil)
		if chapter_id
			if output
				dirname = File.dirname(output)
				extname = File.extname(output)
				basename = File.basename(output, extname)
				filename = File.join(dirname, "#{basename}-#{chapter_id}#{extname}")
			else
				dirname = File.dirname(input)
				basename = File.basename(input, File.extname(input))
				filename = File.join(dirname, "#{basename}-#{chapter_id}.html")
			end
		else
			if output
				filename = output
			else
				dirname = File.dirname(input)
				basename = File.basename(input, File.extname(input))
				filename = File.join(dirname, "#{basename}.html")
			end
		end
		return File.expand_path(filename)
	end
	
	def apply_template(asciidoc_file, input_file, output_name, template_file, multi_page)
		parser = Parser.new(asciidoc_file)
		if multi_page
			File.unlink(asciidoc_file)
			assign_chapter_filenames_and_heading_basenames(parser.chapters, input_file, output_name)
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
	
	def assign_chapter_filenames_and_heading_basenames(chapters, input_file, output_name)
		chapters.each_with_index do |chapter, i|
			if chapter.is_preamble?
				chapter.filename = determine_output_filename(input_file, output_name)
			else
				title_sha1 = Digest::SHA1.hexdigest(chapter.title_without_numbers)
				chapter.filename = determine_output_filename(input_file,
					output_name, title_sha1.slice(0..7))
				chapter.heading.basename = File.basename(chapter.filename)
				chapter.heading.each_descendant do |h|
					h.basename = File.basename(chapter.filename)
				end
			end
		end
	end
end

end
