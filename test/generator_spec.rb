require File.expand_path(File.dirname(__FILE__) + "/spec_helper")
require 'mizuho/parser'

describe Mizuho::Generator do
	describe "#determine_output_filename" do
		before :each do
			@generator = Mizuho::Generator.new("unused argument")
			File.should_receive(:expand_path).with(an_instance_of(String)).any_number_of_times.and_return do |value|
				value
			end
		end
		
		describe "if chapter ID is not given" do
			it "changes the input filename's extension to .html, if " <<
			   "the output filename is not given and the input " <<
			   "filename has an extension" do
				output = @generator.send(:determine_output_filename, "/foo/input.txt")
				output.should == "/foo/input.html"
				
				output = @generator.send(:determine_output_filename, "/foo/input.txt.erb")
				output.should == "/foo/input.txt.html"
			end
			
			it "appends .html to the input filename, if the output " <<
			   "filename is not given and the input filename has no " <<
			   "extension" do
				output = @generator.send(:determine_output_filename, "/foo/input.txt.erb/abc")
				output.should == "/foo/input.txt.erb/abc.html"
			end
			
			it "uses the given output filename, if given" do
				output = @generator.send(:determine_output_filename, "/foo/input.txt", "/hi.jpg")
				output.should == "/hi.jpg"
			end
		end
		
		describe "if chapter ID is given" do
			it "changes the input filename's extension to .html and " <<
			   "prepends the chapter ID to the extension, if the " <<
			   "output filename is not given" do
				output = @generator.send(:determine_output_filename, "/foo/input.txt", nil, "123")
				output.should == "/foo/input-123.html"
				output = @generator.send(:determine_output_filename, "/foo/input.txt.erb", nil, "123")
				output.should == "/foo/input.txt-123.html"
			end
			
			it "it prepends the chapter ID in front of the extension, " <<
			   "if the output filename is given and has an extension" do
				value = @generator.send(:determine_output_filename, "/foo/input.txt", "/hi.jpg", "123")
				value.should == "/hi-123.jpg"
			end
			
			it "it appends the chapter ID to the filename, if the " <<
			   "output filename is given and doesn't have an extension" do
				value = @generator.send(:determine_output_filename, "/foo/input.txt", "/hi", "123")
				value.should == "/hi-123"
			end
		end
	end
end
