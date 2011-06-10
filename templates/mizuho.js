// IE...
if (!Date.now) {
	Date.now = function() {
		return new Date().getTime();
	}
}

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
	smoothScrolling: true,
	
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
		
		if (this.isMobileDevice()) {
			$(document.body).addClass('mobile');
		}
	},
	
	isMobileDevice: function() {
		return navigator.userAgent.match(
			/(IEMobile|Windows CE|NetFront|PlayStation|PLAYSTATION|like Mac OS X|MIDP|UP\.Browser|Symbian|Nintendo|Android)/
		);
	},
	
	virtualAnimate: function(options) {
		var options = $.extend({
			duration: 1000
		}, options || {});
		var animation_start = Date.now();
		var animation_end = Date.now() + options.duration;
		var interval = animation_end - animation_start;
		this._virtualAnimate_step(animation_start, animation_end, interval, options);
	},

	_virtualAnimate_step: function(animation_start, animation_end, interval, options) {
		var self = this;
		var now = new Date();
		var progress = (now - animation_start) / interval;
		if (progress > 1) {
			progress = 1;
		}
		progress = (1 + Math.sin(-Math.PI / 2 + progress * Math.PI)) / 2;
		options.step(progress);
		if (now < animation_end) {
			setTimeout(function() {
				self._virtualAnimate_step(animation_start,
					animation_end, interval, options);
			}, 15);
		} else {
			options.step(1);
			if (options.finish) {
				options.finish();
			}
		}
	},
	
	smoothlyScrollTo: function(top) {
		if (!this.smoothScrolling) {
			return this.setScrollTop(top);
		}
		
		var self = this;
		var $document = this.$document;
		var current = $document.scrollTop();
		this.virtualAnimate({
			duration: 300,
			step: function(x) {
				$document.scrollTop(Math.floor(
					top + (1 - x) * (current - top)
				));
			},
			finish: function() {
				self.setScrollTop(top);
			}
		});
	},
	
	smoothlyScrollToToc: function() {
		this.smoothlyScrollTo($('#toc').position().top);
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
	
	scrollToHeader: function(header) {
		this.smoothlyScrollTo($(header).offset().top - 50);
	},
	
	setScrollTop: function(top, element) {
		// Browsers don't always scroll properly so work around
		// this with a few timers.
		var self = this;
		element = element || this.$document;
		element = $(element);
		element.scrollTop(top);
		setTimeout(function() {
			element.scrollTop(top);
		}, 1);
		setTimeout(function() {
			element.scrollTop(top);
			self.$document.trigger('mizuho:updateTopBar');
		}, 20);
	},
	
	internalLinkClicked: function(link, event) {
		event.preventDefault();
		var hash = $(link).attr('href');
		var $header = this.lookupHeader(hash);
		this.scrollMemory[location.hash] = this.$document.scrollTop();
		if ($header) {
			this.scrollToHeader($header);
		}
		this.changingHash = true;
		this.activeHash = location.hash = hash;
	},
	
	reinstallInternalLinks: function() {
		var self = this;
		$('a').each(function() {
			var $this = $(this);
			var href = $this.attr('href');
			if (href[0] == '#' && !href.match(/^#\!/)) {
				$this.attr('href', href.replace(/^#/, '#!/'));
				$this.click(function(event) {
					self.internalLinkClicked(this, event);
				});
			}
		});
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
				self.scrollToHeader($header);
			} else if (location.hash == '#!/') {
				self.setScrollTop(0);
			}
			scrollMemory[location.hash] = $document.scrollTop();
			self.activeHash = location.hash;
		}
		
		this.reinstallInternalLinks();
		$window.one('load', function() {
			setTimeout(function() {
				self.reinstallInternalLinks();
			}, 20);
		});
		
		$window.hashchange(hashChanged);
		if (!location.hash.match(/#!\//)) {
			// Workaround to ensure that Chrome adds the initial
			// hash change to '#!/' to its back button history.
			$window.one('load', function() {
				setTimeout(function() {
					self.changingHash = true;
					self.activeHash = location.hash = '#!/';
				}, 20);
			});
		} else {
			$window.one('load', function() {
				self.smoothScrolling = false;
				hashChanged();
				self.smoothScrolling = true;
			});
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
		Mizuho[key] = $.proxy(Mizuho[key], Mizuho);
	}
}
$(document).ready(Mizuho.initialize);
$(document).ready(Mizuho.installHashbangLinks);
