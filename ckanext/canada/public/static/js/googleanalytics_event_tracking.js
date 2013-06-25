// Add Google Analytics Event Tracking to resource download links.
jQuery('a.resource-url-analytics').on('click', function() {
    var resource_url = encodeURIComponent(jQuery(this).prop('href'));
    if (resource_url) {
      _gaq.push(['_trackEvent', 'Resource', 'Download', resource_url]);
    }
});
