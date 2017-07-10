	$(document).ready(function(){
		var ws;
		var has_error = false;
		var num = 0;
		var last = 0;
		announce = function(c,m) {
			var inf = $("div#info");
			inf.empty();
			// var li = $('<div class="alert alert-'+c+'" />');
			var li = $('<div/>');
			num = num+1;
			var n = num;
			li.attr('id', 'alert-'+n)
			li.addClass('alert');
			li.addClass('alert-'+c);
			li.addClass('fade');
			li.addClass('fade in');
			li.text(m);
			inf.prepend(li);
			$('#page').scrollTop(0);
			if (last > 0)
			{
				$('#alert-'+last).alert('close')
			}
			if (c == "danger") {
				last = n;
			} else {
				setTimeout(function(){ 
					$('#alert-'+n).alert('close')
				}, 2000);
			}
		}
		//$('form#sender').submit(function(event){
		//	ws.send(JSON.stringify({"type":["note"],"data": $('input#data').val() }));
		//	$('textarea#data').val("");
		//	return false;
		//});
		if ("WebSocket" in window && "moat" in window && "host" in window.moat) {
			announce("info","Connecting …")
			var ws = new WebSocket("ws://" + window.moat.host +"/api/control");
			var backlogging = true;

			ws.onmessage = function (msg) {
				var m = $.parseJSON(msg.data);
				console.log("IN",m);
				if (!('action' in m)) {
					announce("warning","Unknown message: " + m)
				} else if (m.action == 'error') {
					announce("danger",m.msg)
				} else if (m.action == 'replace') {
					var f = $('#'+m.id);
					var d = $(m.data);
					d.attr("id",m.id)
					if (f.length > 0) {
						f.replaceWith(d);
					} else {
						f = $('#c'+m.parent);
						if (f.length == 0)  {
							f = $('#'+m.parent);
							if (f.length == 0)  {
								announce("danger","Content ID "+m.id+"/"+m.parent+" not found.");
								return;
							}
						}
						f.append(d);
					}

				}
			};
			ws.onopen = function (msg) {
			    announce("success","Connected. Waiting for instructions …");
				ws.send(JSON.stringify({"action":"locate","location": "" }));
			};
			ws.onerror = function (msg) {
				announce("danger","Connection error! Please reload this page.");
			};
			ws.onclose = function (msg) {
				if (has_error) { return; }
				announce("danger","Connection closed.");
			};
		} else if ("WebSocket" in window) {
			announce("danger","Internal error! Please try again later.");
		} else {
			announce("info","Your browser does not support WebSockets. Sorry.");
		}


		// $.idleTimer(300000); // Hochscrollen nach 5min
		// $(document).bind("idle.idleTimer", function(){
			// $('#page').scrollTop(0);
		// });

	});
