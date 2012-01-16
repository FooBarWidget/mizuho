// IE...
if (!Date.now) {
	Date.now = function() {
		return new Date().getTime();
	}
}

var Mizuho = {
	/** Cached DOM elements so that we don't have to re-find them over and over. */
	$document: undefined,
	$window: undefined,
	$mainSections: undefined,
	$sectionHeaders: undefined,

	/** Constants */
	MAX_TOC_LEVEL: 3,

	sectionHeadersSelector: undefined,
	scrollMemory: {},
	changingHash: false,
	activeHash: undefined,
	/** Whether in single-page or multi-page mode. Either 'single' or 'multi'. */
	mode: 'single',
	/** Whether smooth scrolling is enabled. It is always enabled except right
	 * after page load: when the page is scrolled to the section as pointed to
	 * by location.hash.
	 */
	smoothScrolling: true,
	
	initialize: function() {
		this.sectionHeadersSelector = '';
		for (var i = 0; i < this.MAX_TOC_LEVEL; i++) {
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
	

	/********* Generic utility functions *********/

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
	

	/********* Mizuho-specific functions *********/

	/** Returns the currently displayed section's header DOM element. */
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
	
	/** Looks up a section's header DOM element corresponding to a hash name. */
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
	}
};

for (var key in Mizuho) {
	if (typeof(Mizuho[key]) == 'function') {
		Mizuho[key] = $.proxy(Mizuho[key], Mizuho);
	}
}
$(document).ready(Mizuho.initialize);
//$(document).ready(Mizuho.installHashbangLinks);
