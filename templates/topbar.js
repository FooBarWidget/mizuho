Mizuho.initializeTopBar = function() {
	var self = this;
	var timerId;
	var h = $('#topbar');
	//var toc2 = $('<div id="toc2"></div>').html($('#toc').html()).insertAfter(h);
	var title = $('#header h1');
	
	function scheduleScrollUpdate() {
		if (timerId !== undefined) {
			return;
		}
		timerId = setTimeout(function() {
			timerId = undefined;
		
			if (title.offset().top + title.height() < self.$document.scrollTop()) {
				if (!h.is(':visible')) {
					h.slideDown();
				}
			} else {
				if (h.is(':visible')) {
					h.slideUp();
				}
			}
		
			//var diff = $(document).scrollTop() - title.offset().top;
			//h.css('top', Math.min(diff - h.height(), 0) + 'px');
		
			var header = self.currentSubsection();
			var name;
			if (header) {
				name = $(header).text();
			} else {
				name = 'Preamble';
			}
			$('#current_section').text(name);
		}, 100);
	}
	
	this.$document.scroll(scheduleScrollUpdate);
}.bind(Mizuho);

$(document).ready(Mizuho.initializeTopBar);
