function loadComments() {
	function normalizeHeaderTitle(title) {
		return $.trim(title);
	}
	
	$('#content .comments').each(function() {
		var header = $(this).next();
		console.log(header.text());
	})
}

$(document).ready(loadComments);
