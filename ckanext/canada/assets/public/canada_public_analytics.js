window.addEventListener('load', function(){
  // Add Google Analytics Event Tracking to resource download links.
  //TODO: rewrite ga method to gtag method
  jQuery('a.resource-url-analytics').on('click', function() {
    var resource_url = encodeURIComponent($(this).prop('href'));
    if (resource_url) {
      ga('send', {
        hitType: 'event',
        eventCategory: 'resource',
        eventAction: 'download',
        eventLabel: resource_url,
        dimension1: $(this).data('res-id'),
        dimension2: $(this).data('pkg-id'),
        dimension3: $(this).data('org-id')
      });
    }
  });
});
