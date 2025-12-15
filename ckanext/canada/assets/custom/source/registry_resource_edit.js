window.addEventListener('load', function(){

  $(document).ready(function() {

    let editToolbar = $('header.page-header ul.nav-tabs');

    if ( editToolbar.length > 0 ){

      let activeElement = $(editToolbar).find('li.active');

      if ( activeElement.length === 0 ){

        // if there is no active element, assume that we are editing the metadata
        $(editToolbar).find('li').first().addClass('active');

      }

    }

    let resourceDataFieldWrapper = $('.resource-upload-field');

    if ( resourceDataFieldWrapper.length > 0 ){

      let errorBlocks = $(resourceDataFieldWrapper).find('.error-block');

      if ( errorBlocks.length > 0 ){

        $(errorBlocks).each(function(_index, _element){

          if ( _index === 0 ){
            $(_element).appendTo(resourceDataFieldWrapper);
          }else{
            $(_element).remove();
          }

        });

      }

    }

  });

});
