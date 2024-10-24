window.addEventListener('load', function(){
  $(document).ready(function() {

    let actionTabContainer = $('.recombinant-action-panels-container');

    if( actionTabContainer.length > 0 ){

      let activityTab = $(actionTabContainer).find('#activity-lnk');

      if( activityTab.length > 0 ){

        let link = $('#activity').find('a').first().attr('href');

        if( link && link.length > 0 ){

          $(activityTab).attr('href', link);
          $(activityTab).removeAttr('aria-controls');
          $(activityTab).attr('tabindex', 0);

          $(activityTab).off('click');
          $(activityTab).off('keyup');

          function _goto_activity(){
            window.location = link;
          }

          $(activityTab).on('click.Link', function(_event){
            _event.preventDefault();
            _goto_activity();
          });
          $(activityTab).on('keyup.Link', function(_event){
            let keyCode = _event.keyCode ? _event.keyCode : _event.which;
            // space and enter keys required for a11y
            if( keyCode == 32 || keyCode == 13 ){
              _event.preventDefault();
              _goto_activity();
            }
          });

        }

      }

    }

  });
});
