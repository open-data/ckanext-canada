/*
 Add Google Analytics Event Tracking to actions on the Registry
 */
function trackEvent(id, category, action = undefined) {
  let element = document.getElementById(id);
  if (element) {
    if (action === undefined) {
      var headings = document.getElementsByTagName('H1');
      action = headings.length > 0
          ? headings[0].innerHTML
          : element.innerHTML;
    }

    let url = null;
    if (element.tagName === 'BUTTON')
      url = element.formAction;
    else if (element.tagName === 'A')
      url = element.href;

    if (category && action && url) {
      ga('send', {
        hitType: 'event',
        eventCategory: category,
        eventAction: action,
        eventLabel: url,
      });
    }
  }
}

window.onload = function() {
  if (document.getElementById('login-invalid'))
    trackEvent('login-invalid', 'login', 'Invalid login');
};
