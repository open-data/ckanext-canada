window.addEventListener('load', function(){

  $(document).ready(function() {

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
