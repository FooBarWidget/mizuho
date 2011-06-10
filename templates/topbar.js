Mizuho.isMobileDevice = $.proxy(function() {
	return navigator.userAgent.match(
		/(IEMobile|Windows CE|NetFront|PlayStation|PLAYSTATION|like Mac OS X|MIDP|UP\.Browser|Symbian|Nintendo|Android)/
	);
}, Mizuho);

Mizuho.initializeTopBar = $.proxy(function() {
	var $window = this.$window;
	var $document = this.$document;
	var self = this;
	var $topbar = $('#topbar');
	var $title = $('#header h1');
	var $currentSection = $('#current_section');
	var isMobileDevice = this.isMobileDevice();
	var timerId;
	
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
	
	function showFloatingToc() {
		// Highlight current TOC entry.
		var currentSubsection = self.currentSubsection();
		$floattoclinks.removeClass('current');
		if (currentSubsection) {
			var currentSubsectionTitle = $(currentSubsection).text();
			$floattoclinks.each(function() {
				if ($(this).text() == currentSubsectionTitle) {
					$(this).addClass('current');
					
					// scrollIntoView() may change the
					// document's scrolltop too even though
					// we only want to scroll the floating
					// TOC, so restore the scrolltop
					// afterwards.
					var origScrollTop = $document.scrollTop();
					this.scrollIntoView();
					self.setScrollTop(
						$floattoc.scrollTop() - $floattoc.height() * 0.45,
						$floattoc);
					self.setScrollTop(origScrollTop);
					
					return false;
				}
			});
		}
		
		// Layout and display floating TOC.
		var origScrollTop = $document.scrollTop();
		var windowWidth = $window.width();
		var maxRight = windowWidth - Math.floor(windowWidth * 0.1);
		
		if ($currentSection.offset().left + $floattoc.outerWidth() > maxRight) {
			$floattoc.css('left', maxRight - $floattoc.outerWidth());
		} else {
			$floattoc.css('left', $currentSection.offset().left + 'px');
		}
		if (isMobileDevice) {
			$floattoc.css({
				top: $currentSection.offset().top +
					$currentSection.innerHeight() +
					'px',
				height: $window.height() * 0.7
			});
		}
		$floattoc.css('visibility', 'visible');
		$currentSection.addClass('pressed');
		
		function hideFloatingToc() {
			$currentSection.removeClass('pressed');
			$floattoc.css('visibility', 'hidden');
			$floattoclinks.unbind('click', hideFloatingToc);
			$document.unbind('mousedown', onMouseDown);
			$document.unbind('mizuho:hideTopBar', hideFloatingToc)
			$window.unbind('scroll', onScroll);
		}
		
		function onMouseDown(event) {
			if (event.target != $floattoc[0]
			 && $(event.target).closest('#floattoc').length == 0) {
				hideFloatingToc();
			}
		}
		
		function onScroll(event) {
			if ($document.scrollTop() != origScrollTop) {
				hideFloatingToc();
			}
		}
		
		$floattoclinks.bind('click', hideFloatingToc);
		$document.mousedown(onMouseDown);
		$document.bind('mizuho:hideTopBar', hideFloatingToc);
		$window.bind('scroll', onScroll);
	}
	
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
				width: $window.width() + 'px'
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
