var disqus_identifier;
var disqus_title;
var disqus_url;
var disqus_developer = 1;

Mizuho.initializeCommenting = $.proxy(function() {
	var self = this;
	this.commentBalloons = $('.comments');
	this.commentBalloons.click(function() {
		self.showCommentsPopup(this);
	});
	this.reloadCommentCount();
}, Mizuho);

Mizuho.showLightbox = $.proxy(function(creationCallback, closeCallback) {
	var lightbox = $(
		'<div id="comments_lightbox">' +
		'  <div id="comments_lightbox_shadow"></div>' +
		'  <div id="comments_lightbox_contents"><div class="shell"></div></div>' +
		'</div>');
	var shadow = $('#comments_lightbox_shadow', lightbox);
	var contents = $('#comments_lightbox_contents > .shell', lightbox);
	
	function close() {
		if (lightbox) {
			lightbox.remove();
			lightbox = undefined;
			if (closeCallback) {
				closeCallback();
			}
		}
	}

	shadow.click(close);
	lightbox.bind('lightbox:close', close);
	lightbox.appendTo(document.body);
	creationCallback(contents);
}, Mizuho);

Mizuho.getCommentThreadInfo = $.proxy(function(balloon) {
	var info = {};
	if ($(balloon).closest('#toc').length > 0) {
		info.id = 'toctitle';
		info.topic = 'toctitle';
		info.title = $('#header h1').text() + " - " + $('#toctitle').text();
	} else {
		var header = $(balloon).next('h2, h3, h4');
		if (header.length > 0) {
			info.id = header.attr('id');
			info.topic = header.data('comment-topic');
			info.title = $('#header h1').text() + " - " + header.text();
		} else {
			info = undefined;
		}
	}
	return info;
}, Mizuho);

Mizuho.callJuviaApi = function(action, options) {
	function makeQueryString(options) {
		var key, params = [];
		for (key in options) {
			params.push(
				encodeURIComponent(key) +
				'=' +
				encodeURIComponent(options[key]));
		}
		return params.join('&');
	}

	// Makes sure that each call generates a unique URL, otherwise
	// the browser may not actually perform the request.
	if (!('_juviaRequestCounter' in window)) {
		window._juviaRequestCounter = 0;
	}

	var url =
		JUVIA_URL + '/api/' + action +
		'?_c=' + window._juviaRequestCounter +
		'&' + makeQueryString(options);
	window._juviaRequestCounter++;
	
	var s       = document.createElement('script');
	s.async     = true;
	s.type      = 'text/javascript';
	s.className = 'juvia';
	s.src       = url;
	(document.getElementsByTagName('head')[0] ||
	 document.getElementsByTagName('body')[0]).appendChild(s);
}

Mizuho.showCommentsPopup = $.proxy(function(balloon) {
	var info = this.getCommentThreadInfo(balloon);
	if (!info) {
		return;
	}
	
	var self = this;
	this.showLightbox(function(element) {
		// We install a 'Close' button in the Juvia comment form after it has loaded.
		function installCloseButton() {
			if ($('#comments .juvia-form-actions').size() > 0) {
				// The Juvia form is now loaded. Install the button.
				var div = $('<div class="juvia-action" style="margin-left: 0.5em"></div>');
				var button = $('<input type="button" value="Cancel"></div>').appendTo(div);
				div.insertBefore('#comments .juvia-form-actions .juvia-error');
				button.click(function() {
					$(element).trigger('lightbox:close');
				});
			} else {
				// Continue polling.
				setTimeout(installCloseButton, 50);
			}
		}
		setTimeout(installCloseButton, 50);

		// Now load the Juvia comments form.
		element.html('<div id="comments">Loading comments...</div>');
		self.changingHash = true;
		location.hash = '#!/' + info.id;
		self.callJuviaApi('show_topic.js', {
			container   : '#comments',
			site_key    : JUVIA_SITE_KEY,
			topic_key   : info.topic,
			topic_url   : location.href,
			topic_title : info.topic,
			include_base: !window.Juvia,
			include_css : !window.Juvia
		});
	}, function() {
		self.reloadCommentCount();
	});
}, Mizuho);

Mizuho.reloadCommentCount = $.proxy(function() {
	this.callJuviaApi('list_topics.jsonp', {
		site_key: JUVIA_SITE_KEY,
		jsonp   : 'Mizuho.topicListReceived'
	});
}, Mizuho);

Mizuho.topicListReceived = $.proxy(function(result) {
	var self = this;
	var i, topic, map = {};
	for (i = 0; i < result.topics.length; i++) {
		topic = result.topics[i];
		map[topic.key] = topic;
	}

	this.commentBalloons.each(function() {
		var info = self.getCommentThreadInfo(this);
		if (info) {
			topic = map[info.topic];
			if (topic) {
				var balloon = $(this);
				$('.count', balloon).text(topic.comment_count);
				balloon.removeClass('empty');
				balloon.addClass('nonempty');
				balloon.attr('title', null);
			}
		}
	});
}, Mizuho);

$(document).ready(Mizuho.initializeCommenting);
