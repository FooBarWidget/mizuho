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
	
	function lookupHeader(hash) {
		var id = hash.replace(/^#!\//, '#');
		if (id == '') {
			return undefined;
		} else {
			return $(id);
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
	
	$('a').each(function() {
		var $this = $(this);
		var href = $this.attr('href');
		if (href[0] == '#') {
			$this.attr('href', href.replace(/^#/, '#!/'));
			$this.click(internalLinkClicked);
		}
	});
	
	$(window).hashchange(hashChanged);
	if (location.hash == '') {
		changingHash = true;
		location.hash = '#!/';
	} else {
		hashChanged();
	}
}

// Give internal links the hashbang format so that Google Chrome's
// back button works properly and so that Disqus can uniquely identify
// sections.
function installHashbangLinks() {
	var $document = $(document);
	var scrollMemory = window.scrollMemory = {};
	var changingHash = false;
	var activeHash;
	
	function lookupHeader(hash) {
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
	
	function setScrollTop(top) {
		$document.scrollTop(top);
		setTimeout(function() {
			$document.scrollTop(top);
		}, 1);
	}
	
	function hashChanged() {
		if (changingHash) {
			changingHash = false;
			return;
		}
		
		var header = lookupHeader(location.hash);
		if (activeHash !== undefined) {
			scrollMemory[activeHash] = $document.scrollTop();
		}
		if (scrollMemory[location.hash] !== undefined) {
			setScrollTop(scrollMemory[location.hash]);
		} else if (header) {
			header[0].scrollIntoView();
		} else if (location.hash == '#!/' || location.hash == '') {
			setScrollTop(0);
		}
		scrollMemory[location.hash] = $document.scrollTop();
		activeHash = location.hash;
	}
	
	function internalLinkClicked(event) {
		event.preventDefault();
		var hash = $(this).attr('href');
		var header = lookupHeader(hash);
		if (header) {
			header[0].scrollIntoView();
		}
		scrollMemory[location.hash] = $document.scrollTop();
		changingHash = true;
		activeHash = location.hash = hash;
	}
	
	$('a').each(function() {
		var $this = $(this);
		var href = $this.attr('href');
		if (href[0] == '#') {
			$this.attr('href', href.replace(/^#/, '#!/'));
			$this.click(internalLinkClicked);
		}
	});
	
	$(window).hashchange(hashChanged);
	if (!location.hash.match(/#!\//)) {
		changingHash = true;
		activeHash = location.hash = '#!/';
	} else {
		hashChanged();
	}
}

$(document).ready(installHashbangLinks);
