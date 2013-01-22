Mizuho.initializeTopBar = $.proxy(function() {
	var $window = this.$window;
	var $document = this.$document;
	var self = this;
	var $topbar = $('#topbar');
	var $title = $('#header h1');
	var $currentSection = $('#current_section');
	var isMobileDevice = this.isMobileDevice();
	var timerId;
	
	// Create the floating table of contents used in the top bar.
	var $floattoc = $('<div id="floattoc"></div>').html($('#toc').html());
	$floattoc.find('#toctitle').remove();
	$floattoc.find('.comments').remove();
	$floattoc.css('visibility', 'hidden');
	$floattoc.insertAfter($topbar);
	var $floattoclinks = $floattoc.find('a');
	$floattoclinks.each(function() {
		// Firefox changes '#!' to '#%21' so change that back.
		var $this = $(this);
		var href = $this.attr('href');
		if (href.match(/^#%21/)) {
			$this.attr('href', href.replace(/^#%21/, '#!'));
		}
	});
	$floattoclinks.click(function(event) {
		self.internalLinkClicked(this, event);
	});
	
	// Callback for when the user clicks on the Table of Contents
	// button on the top bar.
	function showFloatingToc() {
		var scrollUpdateTimerId;
		
		function reposition() {
			if (isMobileDevice) {
				$floattoc.css({
					top: $currentSection.offset().top +
						$currentSection.innerHeight() +
						'px',
					height: $window.height() * 0.7 + 'px'
				});
			}
		}
		
		function highlightCurrentTocEntry() {
			var currentSubsection = self.currentSubsection();
			$floattoclinks.removeClass('current');
			if (currentSubsection) {
				var currentSubsectionTitle = $(currentSubsection).text();
				var $link;
				
				$floattoclinks.each(function() {
					if ($(this).text() == currentSubsectionTitle) {
						$link = $(this);
						return false;
					}
				});
				if ($link) {
					$link.addClass('current');
					self.setScrollTop(
						$floattoc.scrollTop() +
							$link.position().top -
							$floattoc.height() * 0.45,
						$floattoc);
					return false;
				}
			}
		}
		
		function hideFloatingToc() {
			$currentSection.removeClass('pressed');
			$floattoc.css('visibility', 'hidden');
			$floattoclinks.unbind('click', hideFloatingToc);
			$document.unbind('mousedown', onMouseDown);
			$document.unbind('touchdown', onMouseDown);
			$document.unbind('mizuho:hideTopBar', hideFloatingToc);
			$window.unbind('scroll', onScroll);
			if (scrollUpdateTimerId !== undefined) {
				clearTimeout(scrollUpdateTimerId);
				scrollUpdateTimerId = undefined;
			}
		}
		
		function onMouseDown(event) {
			if (event.target != $floattoc[0]
			 && $(event.target).closest('#floattoc').length == 0) {
				hideFloatingToc();
			}
		}
		
		function onScroll(event) {
			if (scrollUpdateTimerId === undefined) {
				scrollUpdateTimerId = setTimeout(function() {
					scrollUpdateTimerId = undefined;
					reposition();
					highlightCurrentTocEntry();
				}, 100);
			}
		}
		
		// Layout and display floating TOC.
		highlightCurrentTocEntry();
		var origScrollTop = $document.scrollTop();
		var windowWidth = $window.width();
		var maxRight = windowWidth - Math.floor(windowWidth * 0.1);
		
		if ($currentSection.offset().left + $floattoc.outerWidth() > maxRight) {
			$floattoc.css('left', maxRight - $floattoc.outerWidth());
		} else {
			$floattoc.css('left', $currentSection.offset().left + 'px');
		}
		reposition();
		$floattoc.css('visibility', 'visible');
		$currentSection.addClass('pressed');
		
		$floattoclinks.bind('click', hideFloatingToc);
		$document.bind('mousedown', onMouseDown)
		$document.bind('touchdown', onMouseDown);
		$document.bind('mizuho:hideTopBar', hideFloatingToc);
		$window.bind('scroll', onScroll);
	}
	
	// Called whenever the user scrolls. Updates the title of the
	// Table of Contents button in the top bar to the section that
	// the user is currently reading.
	function update() {
		if ($title.offset().top + $title.height() < $document.scrollTop()) {
			if (!$topbar.is(':visible')) {
				$topbar.slideDown(250);
				$document.trigger('mizuho:showTopBar');
			}
		} else {
			if ($topbar.is(':visible')) {
				$topbar.slideUp();
				$document.trigger('mizuho:hideTopBar');
			}
		}
		
		if (isMobileDevice) {
			$topbar.css({
				top: $document.scrollTop() + 'px',
				width: $window.width() -
					parseInt($topbar.css('padding-left')) -
					parseInt($topbar.css('padding-right')) +
					'px'
			});
		}
		
		var header = self.currentSubsection();
		var name;
		if (header) {
			name = $(header).text();
		} else {
			name = 'Preamble';
		}
		$currentSection.text(name);
	}
	
	function scheduleUpdate() {
		if (timerId !== undefined) {
			return;
		}
		timerId = setTimeout(function() {
			timerId = undefined;
			update();
		}, 100);
	}
	
	
	if (isMobileDevice) {
		// Mobile devices don't support position fixed.
		$topbar.css('position', 'absolute');
		$floattoc.css('position', 'absolute');
	}
	
	$currentSection.click(showFloatingToc);
	$window.scroll(scheduleUpdate);
	$document.bind('mizuho:updateTopBar', update);
}, Mizuho);

$(document).ready(Mizuho.initializeTopBar);
