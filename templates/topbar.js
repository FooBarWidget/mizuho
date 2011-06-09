Mizuho.initializeTopBar = function() {
	var $document = this.$document;
	var self = this;
	var $topbar = $('#topbar');
	var $title = $('#header h1');
	var $currentSection = $('#current_section');
	var timerId;
	
	var $floattoc = $('<div id="floattoc"></div>').html($('#toc').html());
	$floattoc.find('#toctitle').remove();
	$floattoc.find('.comments').remove();
	$floattoc.css('visibility', 'hidden');
	$floattoc.insertAfter(topbar);
	var $floattoclinks = $floattoc.find('a');
	$floattoclinks.click(function(event) {
		self.internalLinkClicked(this, event);
	});
	
	function showFloatingToc() {
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
					self.setScrollTop(origScrollTop);
					
					return false;
				}
			});
		}
		
		var windowWidth = self.$window.width();
		var maxRight = windowWidth - Math.floor(windowWidth * 0.1);
		
		if ($currentSection.offset().left + $floattoc.outerWidth() > maxRight) {
			$floattoc.css('left', maxRight - $floattoc.outerWidth());
		} else {
			$floattoc.css('left', $currentSection.offset().left + 'px');
		}
		$floattoc.css('visibility', 'visible');
		
		function hideFloatingToc() {
			$floattoc.css('visibility', 'hidden');
			$floattoclinks.unbind('click', hideFloatingToc);
			$document.unbind('mousedown', onMouseDown);
			$document.unbind('mizuho:hideTopBar', hideFloatingToc)
		}
		
		function onMouseDown(event) {
			if (event.target != $floattoc[0]
			 && $(event.target).closest('#floattoc').length == 0) {
				hideFloatingToc();
			}
		}
		
		$floattoclinks.bind('click', hideFloatingToc);
		$document.mousedown(onMouseDown);
		$document.bind('mizuho:hideTopBar', hideFloatingToc);
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
	
	$currentSection.click(showFloatingToc);
	$document.scroll(scheduleUpdate);
}.bind(Mizuho);

$(document).ready(Mizuho.initializeTopBar);
