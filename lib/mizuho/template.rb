require 'erb'
require 'mizuho/parser'

module Mizuho

class Template
	def initialize(template_file, options)
		@template_file = template_file
		@base_dir = File.expand_path(File.dirname(@template_file))
		@options = options
		options.each_key do |key|
			raise "All option keys must be symbols." if !key.is_a?(Symbol)
			raise "Invalid key name '#{key}'." if key.to_s !~ /\A[a-z0-9_]+\??\Z/i
			eval %{
				def #{key}
					@options[:#{key}]
				end
			}
		end
		apply
	end
	
	def save(output_file)
		File.open(output_file, 'w') do |f|
			f.write(@output_contents)
		end
	end

protected
	include ERB::Util
	
	def include_file(basename)
		return File.read(File.join(@base_dir, basename))
	end
	
private
	def get_binding
		return binding
	end
	
	def apply
		erb = ERB.new(File.read(@template_file), nil, '-')
		@output_contents = eval(erb.src, get_binding, @template_file)
	end
end

end
