window.addEventListener('load', function(){
  // Add Google Analytics Custom Event Tracking to actions.
  $(document).ready(function(){
    let title;
    let referrer = document.referrer;

    // Get the title from the first H1 tag
    if( $('h1').length > 0 ){
      title = $('h1')[0].innerText;
    }

    if( typeof gtag != 'undefined' ){
      // gtag function exists

      let resourceAnalyticsAnchors = $('a.resource-url-analytics');
      if( resourceAnalyticsAnchors.length > 0 ){

        $(resourceAnalyticsAnchors).each(function(_index, _anchor){

          $(_anchor).off('click.analytics');
          $(_anchor).on('click.analytics', function(_event){

            let resourceURL = encodeURIComponent($(_anchor).prop('href'));
            let packageID = $(_anchor).attr('data-pkg-id');
            let resourceID = $(_anchor).attr('data-res-id');
            let organizationID = $(_anchor).attr('data-org-id');
            gtag('event', 'resource', {
              'action': 'Resource Downloaded',
              'resource_url': resourceURL,
              'package_id': packageID,
              'resource_id': resourceID,
              'organization_id': organizationID,
              'title': title,
              'referrer': referrer,
            });

          });

        });

      }

    }// is gtag defined

  });

});
