var disqus_identifier;
var disqus_title;
var disqus_developer = 1;

function loadComments() {
	function showLightbox(creationCallback) {
		var lightbox = $(
			'<div id="comments_lightbox">' +
			'  <div id="comments_lightbox_shadow"></div>' +
			'  <div id="comments_lightbox_contents"><div class="shell"></div></div>' +
			'</div>');
		var shadow = $('#comments_lightbox_shadow', lightbox);
		var contents = $('#comments_lightbox_contents > .shell', lightbox);
		shadow.click(function() {
			lightbox.remove();
		});
		lightbox.appendTo(document.body);
		creationCallback(contents);
	}
	
	function resetDisqus(identifier, title) {
		disqus_identifier = identifier;
		disqus_title = title;
		if (window.DISQUS) {
			window.DISQUS.reset({
				reload: true,
				config: function () {
					this.page.identifier = identifier;
					this.page.url = location.href;
					this.page.title = title;
				}
			});
		} else {
			var dsq = document.createElement('script');
			dsq.type = 'text/javascript';
			dsq.async = true;
			dsq.src = 'http://' + disqus_shortname + '.disqus.com/embed.js';
			(document.getElementsByTagName('head')[0] || document.getElementsByTagName('body')[0]).appendChild(dsq);
		}
	}
	
	function getCommentThreadInfo(balloon) {
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
	}
	
	function showComments() {
		var info = getCommentThreadInfo(this);
		if (!info) {
			return;
		}
		
		showLightbox(function(element) {
			element.html(
				'<div id="comments_notice"><span>Please use <a href="https://gist.github.com/">Gist</a> if you want to post code snippets.</span></div>' +
				'<div id="disqus_thread"></div>' +
				'<a href="http://disqus.com" class="dsq-brlink">comments powered by <span class="logo-disqus">Disqus</span></a>'
			);
			
			var thread = $('#disqus_thread', element);
			var timerID;
			
			function monitorDisqusLoaded() {
				if ($('#dsq-account-dropdown', thread).length > 0) {
					clearInterval(timerID);
					element.addClass('disqus-loaded');
					var likes = $('#dsq-global-toolbar .dsq-global-toolbar-likes', element);
					if ($.trim(likes.html()) != "") {
						element.addClass('align-center');
					}
				}
			}
			
			timerID = setInterval(monitorDisqusLoaded, 50);
			
			location.changingHash = true;
			location.hash = '#!/' + info.id;
			resetDisqus(info.topic, info.title);
		});
	}
	
	var commentBalloons = $('.comments');
	commentBalloons.click(showComments);
	
	var hiddenContainer = $('<div style="height: 0; overflow: hidden"></div>').appendTo(document.body);
	var locationWithoutHash = window.location.href.replace(/#.*/, '');
	var checks = window.checks = [];
	commentBalloons.each(function() {
		var info = getCommentThreadInfo(this);
		if (info) {
			var link = $('<a></a>').appendTo(hiddenContainer);
			link.attr('href', locationWithoutHash + '#!/' + info.id + '#disqus_thread');
			link.attr('data-disqus-identifier', info.topic);
			
			var balloon = $(this);
			function callback(count) {
				if (count > 0) {
					$('.count', balloon).text(count);
					balloon.removeClass('empty');
					balloon.addClass('nonempty');
					balloon.attr('title', null);
				}
			}
			
			checks.push({ element: link[0], callback: callback });
		}
	});
	
	var s = document.createElement('script');
	s.async = true;
	s.type = 'text/javascript';
	s.src = 'http://' + disqus_shortname + '.disqus.com/count.js';
	(document.getElementsByTagName('HEAD')[0] || document.getElementsByTagName('BODY')[0]).appendChild(s);
	
	var timerID;
	timerID = setInterval(function() {
		for (var i = checks.length - 1; i >= 0; i--) {
			if (checks[i].element.childNodes.length > 0) {
				checks[i].callback(parseInt($(checks[i].element).text()));
				checks.splice(i, 1);
			}
		}
		if (checks.length == 0) {
			clearInterval(timerID);
		}
	}, 100);
}

$(document).ready(loadComments);
