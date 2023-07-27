window.addEventListener('load', function(){
  $(document).ready(function() {

    let formatField = $('#field-format');
    if ( formatField.length > 0 ){

      $(formatField).select2({});
      $(formatField).parent()
                    .children('#s2id_field-format')
                    .addClass('conrtol-medium')
                    .removeClass('form-control')
                    .css({'display': 'block'});

    }

    let urlField = $('#field-image-url');
    let uploadField = $('#field-image-upload');
    // TODO: onchange above fields to clear the select2 field and call guess_resource_format endpoint

  });
});
