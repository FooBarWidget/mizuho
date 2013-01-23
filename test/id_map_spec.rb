# Copyright (c) 2012 Hongli Lai
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

require File.expand_path(File.dirname(__FILE__) + "/spec_helper")
require 'stringio'
require 'mizuho/id_map'

module Mizuho

describe IdMap do
	before :each do
		@id_map = IdMap.new
	end

	describe "#generate_associations" do
		describe "if no similar titles exist in the map" do
			before :each do
				@id_map.generate_associations(["Installation",
					"Installation on Linux", "Configuration"])
				@id1 = @id_map.associations["Installation"]
				@id2 = @id_map.associations["Installation on Linux"]
				@id3 = @id_map.associations["Configuration"]
			end

			it "returns a new unique ID" do
				@id1.should_not == @id2
				@id1.should_not == @id3
			end

			it "marks the entry as associated" do
				@id_map.entries["Installation"].should be_associated
				@id_map.entries["Installation on Linux"].should be_associated
				@id_map.entries["Configuration"].should be_associated
			end

			it "doesn't mark the corresponding entry as fuzzy" do
				@id_map.entries["Installation"].should_not be_fuzzy
				@id_map.entries["Installation on Linux"].should_not be_fuzzy
				@id_map.entries["Configuration"].should_not be_fuzzy
			end
		end

		describe "if the same title exists in the map, but with a different section number" do
			before :each do
				@entry1 = @id_map.add("1.2. Installation using a tarball", nil, false, false)
				@entry2 = @id_map.add("5.6. Installation using a tarball", nil, false, false)
				@entry3 = @id_map.add("6.0. Installation using a tarball", nil, false, false)
				@id_map.generate_associations(["5.4. Installation using a tarball",
					"2.1. Installation using a tarball"])
				@id1 = @id_map.associations["5.4. Installation using a tarball"]
				@id2 = @id_map.associations["2.1. Installation using a tarball"]
			end

			it "associates with the title whose section number is closest to the new section number" do
				@id1.should == @entry2.id
				@id2.should == @entry1.id
			end

			it "changes the original entries' titles" do
				@entry1.title.should == "2.1. Installation using a tarball"
				@entry2.title.should == "5.4. Installation using a tarball"
				@entry3.title.should == "6.0. Installation using a tarball"
			end

			it "marks the corresponding entry as associated" do
				@entry1.should be_associated
				@entry2.should be_associated
				@entry3.should_not be_associated
			end

			it "doesn't mark the corresponding entry as fuzzy" do
				@entry1.should_not be_fuzzy
				@entry2.should_not be_fuzzy
				@entry3.should_not be_fuzzy
			end
		end

		describe "if one or more similar titles exist in the map" do
			before :each do
				@entry1 = @id_map.add("Installation using a tarball", nil, false, false)
				@entry2 = @id_map.add("Installation using a Linux tarball", nil, false, false)
			end

			it "associates with the most similar title and returns its ID" do
				@id_map.generate_associations(["Installation using tarball"])
				@id3 = @id_map.associations["Installation using tarball"]
				@id3.should == @entry1.id
				@entry1.title.should == "Installation using tarball"
			end

			it "only associates with a title that hasn't been associated before" do
				@entry1.associated = true
				@id_map.generate_associations(["Installation using tarball"])
				@id3 = @id_map.associations["Installation using tarball"]
				@id3.should == @entry2.id
			end

			it "marks the corresponding entry as associated" do
				@id_map.generate_associations(["Installation using tarball"])
				@id_map.entries["Installation using tarball"].should be_associated
			end

			it "marks the corresponding entry as fuzzy" do
				@id_map.generate_associations(["Installation using tarball"])
				@id_map.entries["Installation using tarball"].should be_fuzzy
			end
		end

		describe "if a one title has a similar match, but a later title has an exact match" do
			it "associates the later title with the exact match, then associates the first title with the similar match" do
				@id_map.add("Hello Dear World", "id-1", false, false)
				@id_map.add("Hallaa Dear World", "id-2", false, false)
				@id_map.generate_associations(["Helloo Dear World", "Hello Dear World"])
				@id_map.associations["Helloo Dear World"].should == "id-2"
				@id_map.associations["Hello Dear World"].should == "id-1"
			end
		end

		specify "title matching is case-insensitive" do
			entry1 = @id_map.add("INSTALLATION USING A TARBALL", nil, false, false)
			@id_map.generate_associations(["installation using tarball"])
			id = @id_map.associations["installation using tarball"]
			id.should == entry1.id
		end
	end

	describe "entries" do
		specify "are sortable by chapter" do
			array = []
			array << IdMap::Entry.new('1. Extra chapter')
			array << IdMap::Entry.new('10. Under the hood')
			array << IdMap::Entry.new('2.1. Generic installation instructions')
			array.sort!
			array[0].title.should == '1. Extra chapter'
			array[1].title.should == '2.1. Generic installation instructions'
			array[2].title.should == '10. Under the hood'
		end
	end

	describe "loading" do
		before :each do
			@io = StringIO.new
			@io.puts "# This is a comment."
			@io.puts ""
			@io.puts "Installation	=>	installation-1"
			@io.puts "Configuration	=>	configuration-2"
			@io.puts "# fuzzy"
			@io.puts "Troubleshooting	=>	troubleshooting-1"
			@io.rewind
		end

		it "marks all entries as 'not associated'" do
			@id_map.load(@io)
			@id_map.entries.each_value { |entry| entry.should_not be_associated }
		end

		it "works" do
			@id_map.load(@io)

			@id_map.entries.should have(3).items
			
			entry = @id_map.entries["Installation"]
			entry.title.should == "Installation"
			entry.id.should == "installation-1"
			entry.should_not be_fuzzy

			entry = @id_map.entries["Configuration"]
			entry.title.should == "Configuration"
			entry.id.should == "configuration-2"
			entry.should_not be_fuzzy

			entry = @id_map.entries["Troubleshooting"]
			entry.title.should == "Troubleshooting"
			entry.id.should == "troubleshooting-1"
			entry.should be_fuzzy
		end
	end

	describe "saving" do
		before :each do
			@io = StringIO.new
			@id_map.add "1. Installation", "installation-1", false, true
			@id_map.add "2. Configuration", "configuration-2", false, true
			@id_map.add "3. Troubleshooting", "troubleshooting-1", true, true
			@id_map.add "4. Administration", "administration-1", true, false
			@id_map.add "5. Uninstallation", "uninstallation-1", false, false
			@id_map.add "0. Introduction", "intro", false, true
		end

		it "saves all entries in alphabetical order, marks fuzzy entries as such and puts unassociated (orphaned) entries at the bottom" do
			@id_map.save(@io)
			@io.string.should ==
				IdMap::BANNER +
				"0. Introduction	=>	intro\n\n" +
				"1. Installation	=>	installation-1\n\n" +
				"2. Configuration	=>	configuration-2\n\n" +
				"# fuzzy\n" +
				"3. Troubleshooting	=>	troubleshooting-1\n\n" +
				"\n" +
				"### These sections appear to have been removed. Please check.\n\n" +
				"# fuzzy\n" +
				"4. Administration	=>	administration-1\n\n" +
				"5. Uninstallation	=>	uninstallation-1\n\n"
		end
	end
end

end # module Mizuho
