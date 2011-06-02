function makeMultiPage() {
	var $toc = $('#toc');
	var $early_preamble = $('#early_preamble');
	var $preamble = $('#preamble');
	var $sections = $('.sect1');
	
	var scrollMemory = {};
	var changingHash;
	
	$toc.show();
	$early_preamble.show();
	$preamble.hide();
	$sections.hide();
	
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
	
	function scrollToHeader(header) {
		if (header.nodeName == 'H2') {
			setScrollTop(0);
		} else {
			header.scrollIntoView();
		}
	}
	
	function hashChanged() {
		if (changingHash) {
			changingHash = false;
			return;
		}
		
		var section;
		scrollMemory[currentSectionName()] = $(document).scrollTop();
		if (location.hash == '') {
			displayFrontPage();
		} else {
			var header = $(location.hash);
			section = header.closest('.sect1');
			if (section.length > 0) {
				displaySection(section);
			} else {
				displayFrontPage();
			}
		}
		
		var scrollTop = scrollMemory[currentSectionName()];
		setScrollTop(scrollTop);
	}
	
	function setScrollTop(top) {
		setTimeout(function() {
			$(document).scrollTop(top);
		}, 1);
	}
	
	function internalLinkClicked(event) {
		event.preventDefault();
		scrollMemory[currentSectionName()] = $(document).scrollTop();
		var hash = $(this).attr('href');
		var header = $(hash);
		var section = header.closest('.sect1');
		displaySection(section);
		scrollToHeader(header[0]);
		changingHash = true;
		location.hash = hash;
	}
	
	$('a').each(function() {
		if ($(this).attr('href')[0] == '#') {
			$(this).click(internalLinkClicked);
		}
	});
	
	$(window).hashchange(hashChanged);
	if (location.hash == '') {
		changingHash = true;
		location.hash = 'frontpage';
	}
}

function loadComments() {
	$('#content .comments').each(function() {
		
	})
}

$(document).ready(makeMultiPage);
