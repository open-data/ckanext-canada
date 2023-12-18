window.addEventListener('load', function(){
  // Add Google Analytics Custom Event Tracking to actions on the Registry
  $(document).ready(function() {
    let user, title;
    let referrer = document.referrer;

    // Get the username from the Logged In toolbar
    if( $('#usr-logged').length > 0 &&
        $('#usr-logged').find('.username').length > 0
    ){
      user = $('#usr-logged').find('.username')[0].innerText;
    }

    // Get the title from the first H1 tag
    if( $('h1').length > 0 ){
      title = $('h1')[0].innerText;
    }

    if( typeof gtag != 'undefined' ){
      // gtag function exists

      let flashes = $('.canada-ga-flash');
      if( flashes.length > 0 ){

        $(flashes).each(function(_index, _flash){

          let event = $(_flash).attr('data-ga-event');
          let action = $(_flash).attr('data-ga-action');
          let message = $(_flash)[0].innerText;

          if( event.length > 0 && action.length > 0 ){

            gtag('event', event, {
              'action': action,
              'message': message,
              'user': user,
              'title': title,
              'referrer': referrer,
            });

          }

        });

      }

      // track Excel template download for recombinant type
      if( $( '#xls_download' ).length > 0 ){
        $("#xls_download").on("click", function(_event){

          gtag('event', 'recombinant', {
            'action': 'Template Downloaded',
            'user': user,
            'title': title,
            'referrer': referrer,
          });

        });
      }

      // track Get Help button click
      if( $('a.get-help-analytics').length > 0 ){
        $('a.get-help-analytics').on('click', function(_event){

          gtag('event', 'user', {
            'action': 'Get Help',
            'user': user,
            'title': title,
            'referrer': referrer,
          });

        });
      }

    }// is gtag defined

  });

});
