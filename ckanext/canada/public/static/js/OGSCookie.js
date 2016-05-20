/********************************************************************************************************
 * Peter-Paul Koch for these cookie functions (http://www.quirksmode.org/js/cookies.html)
 * Chris Majewski: I've made significant changes to adapt for IE9 and prior
 ********************************************************************************************************/
function createCookie(name,value,days) {
	var expires = ""
	if (days) {
		var date = new Date();
		date.setTime(date.getTime()+(days*24*60*60*1000));
		expires = "; expires="+date.toGMTString();
	}
	document.cookie = name+"="+value+expires+"; path=/";
}

function readCookie(name) {
	var nameEQ = name + "=";
	var ca = document.cookie.split(';');
	for(var i=0;i < ca.length;i++) {
		var c = ca[i];
		while (c.charAt(0)==' ') c = c.substring(1,c.length);
		if (c.search(nameEQ) == 0) return decodeURIComponent(c.substring(nameEQ.length,c.length));
	}
	return null;
}

function eraseCookie(name) { createCookie(name,"",-1) }
