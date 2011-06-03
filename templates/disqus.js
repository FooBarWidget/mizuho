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
	
	function showComments() {
		var header = $(this).next('#content h2, #content h3, #content h4');
		var id = header.attr('id');
		var topic = header.data('comment-topic');
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
			location.hash = '#!/' + id;
			resetDisqus(topic, $('#header h1').text() + " - " + header.text());
		});
	}
	
	var commentBalloons = $('#content .comments');
	commentBalloons.click(showComments);
}

$(document).ready(loadComments);
