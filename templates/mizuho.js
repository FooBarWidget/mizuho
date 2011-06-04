var Mizuho = {
	$document: undefined,
	$window: undefined,
	$mainSections: undefined,
	$sectionHeaders: undefined,
	maxTocLevel: 3,
	sectionHeadersSelector: undefined,
	scrollMemory: {},
	changingHash: false,
	activeHash: undefined,
	mode: 'single',
	
	initialize: function() {
		this.sectionHeadersSelector = '';
		for (var i = 0; i < this.maxTocLevel; i++) {
			if (i != 0) {
				this.sectionHeadersSelector += ', ';
			}
			this.sectionHeadersSelector += 'h' + (i + 2);
		}
		
		this.$document = $(document);
		this.$window = $(window);
		this.$mainSections = $('.sect1');
		this.$sectionHeaders = $(this.sectionHeadersSelector, '#content');
		this.$sectionHeaders.sort(function(a, b) {
			var off_a = $(a).offset();
			var off_b = $(b).offset();
			return off_a.top - off_b.top;
		});
	},
	
	currentSubsection: function() {
		var $sectionHeaders = this.$sectionHeaders;
		var scrollTop = this.$document.scrollTop();
		var windowHeight = this.$window.height();
		var offset;
		
		var low = 0;
		var high = this.$sectionHeaders.length - 1;
		var mid = 0;
		
		while (low <= high) {
			mid = Math.floor((low + high) / 2);
			offset = $($sectionHeaders[mid]).offset();
			
			if (offset.top >= scrollTop) {
				high = mid - 1;
			} else {
				low = mid + 1;
			}
		}
		
		var $found = $($sectionHeaders[low]);
		if ($found.offset().top > scrollTop + windowHeight) {
			if (low > 0) {
				return $sectionHeaders[low - 1];
			} else {
				return undefined;
			}
		} else {
			return $sectionHeaders[low];
		}
	},
	
	lookupHeader: function(hash) {
		var id = hash.replace(/^#!\//, '#');
		if (id == '') {
			return undefined;
		} else {
			var header = $(id);
			if (header.length == 0) {
				return undefined;
			} else {
				return header;
			}
		}
	},
	
	setScrollTop: function(top) {
		var $document = this.$document;
		$document.scrollTop(top);
		setTimeout(function() {
			$document.scrollTop(top);
		}, 1);
		setTimeout(function() {
			$document.scrollTop(top);
		}, 20);
	},
	
	// Give internal links the hashbang format so that Google Chrome's
	// back button works properly and so that Disqus can uniquely identify
	// sections.
	installHashbangLinks: function() {
		var self = this;
		var $document = this.$document;
		var $window = this.$window;
		var scrollMemory = this.scrollMemory;
		
		function hashChanged() {
			if (self.changingHash) {
				self.changingHash = false;
				return;
			}
			
			var $header = self.lookupHeader(location.hash);
			if (self.activeHash) {
				scrollMemory[self.activeHash] = $document.scrollTop();
			}
			if (scrollMemory[location.hash] !== undefined) {
				self.setScrollTop(scrollMemory[location.hash]);
			} else if ($header) {
				$header[0].scrollIntoView();
			} else if (location.hash == '#!/') {
				self.setScrollTop(0);
			}
			scrollMemory[location.hash] = $document.scrollTop();
			self.activeHash = location.hash;
		}
		
		function internalLinkClicked(event) {
			event.preventDefault();
			var hash = $(this).attr('href');
			var $header = self.lookupHeader(hash);
			scrollMemory[location.hash] = $document.scrollTop();
			if ($header) {
				$header[0].scrollIntoView();
			}
			self.changingHash = true;
			self.activeHash = location.hash = hash;
		}
		
		$('a').each(function() {
			var $this = $(this);
			var href = $this.attr('href');
			if (href[0] == '#') {
				$this.attr('href', href.replace(/^#/, '#!/'));
				$this.click(internalLinkClicked);
			}
		});
		
		$window.hashchange(hashChanged);
		if (!location.hash.match(/#!\//)) {
			// Workaround to ensure that Chrome adds the initial
			// hash change to '#!/' to its back button history.
			$window.one('load', function() {
				setTimeout(function() {
					this.changingHash = true;
					this.activeHash = location.hash = '#!/';
				}, 20);
			});
		} else {
			$window.one('load', hashChanged);
		}
	},
	
	makeMultiPage: function() {
		var $toc = $('#toc');
		var $preamble = $('#preamble');
		var $mainSections = $('.sect1');
		var scrollMemory = this.scrollMemory;
		
		$toc.show();
		$preamble.hide();
		$mainSections.hide();
		
		function currentSectionName() {
			var section = $('.sect1:visible > h2');
			if (section.length > 0) {
				return section.text();
			} else {
				return 'front-page';
			}
		}
		
		function displayFrontPage() {
			$toc.show();
			$early_preamble.show();
			$preamble.hide();
			$sections.hide();
		}
		
		function displaySection(section) {
			if (!section.is(':visible')) {
				$toc.hide();
				$early_preamble.hide();
				$preamble.hide();
				$sections.hide();
				section.show();
			}
		}
		
		function hashChanged() {
			if (changingHash) {
				changingHash = false;
				return;
			}

			var header, section;
			scrollMemory[currentSectionName()] = $(document).scrollTop();
			var header = lookupHeader(location.hash);
			if (header && header.length > 0) {
				section = header.closest('.sect1');
				if (section.length > 0) {
					displaySection(section);
				} else {
					displayFrontPage();
				}
			} else {
				displayFrontPage();
			}

			var scrollTop = scrollMemory[currentSectionName()];
			setScrollTop(scrollTop);
		}
		
		function setScrollTop(top) {
			$(document).scrollTop(top);
			setTimeout(function() {
				$(document).scrollTop(top);
			}, 1);
		}
		
		function internalLinkClicked(event) {
			event.preventDefault();
			scrollMemory[currentSectionName()] = $(document).scrollTop();
			var hash = $(this).attr('href');
			var header = lookupHeader(hash);
			var section = header.closest('.sect1');
			displaySection(section);
			scrollToHeader(header[0]);
			changingHash = true;
			location.hash = hash;
		}
	}
};

for (var key in Mizuho) {
	if (typeof(Mizuho[key]) == 'function') {
		Mizuho[key] = Mizuho[key].bind(Mizuho);
	}
}
$(document).ready(Mizuho.initialize);
$(document).ready(Mizuho.installHashbangLinks);
