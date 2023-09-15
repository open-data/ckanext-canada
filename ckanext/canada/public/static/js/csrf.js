window.addEventListener('load', function(){

  $(document).ready(function(){

    let confirmActions = $("[data-module='confirm-action']");

    if( confirmActions.length > 0 ){

      $(confirmActions).each(function(){

        let form = $(this).closest('form');
        let href_attr = $(this).attr('href');

        let hasToken = false;

        if (
          href_attr.length > 0 &&
          (
            href_attr.includes('?token') ||
            href_attr.includes('&token')
          )
        ){

          hasToken = true;

        }

        // only use the closest form if it exists
        // and if the confirm-action html element
        // does not have a token in the href attribute
        if ( form.length > 0 && ! hasToken ){
          $(this).attr('data-module-with-data', 'true');
        }

      });

    }

  });

});
