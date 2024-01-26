window.addEventListener('load', function(){
  $(document).ready(function() {

    let dataUploadWrapper = $('.resource-upload-field.form-group');

    let formatField = $('#field-format');
    if ( formatField.length > 0 ){

      // initialize select2 for the Resource Format field
      $(formatField).select2({});
      $(formatField).parent()
                    .children('#s2id_field-format')
                    .addClass('conrtol-medium')
                    .removeClass('form-control')
                    .css({'display': 'block'});

    }

    function _guess_mimetype(url){
      $.ajax({
        'url': '/api/action/canada_guess_mimetype',
        'type': 'POST',
        'dataType': 'JSON',
        'data': {
          'url': url,
        },
        'complete': function(_data){
          if( _data.responseJSON && _data.responseJSON.success ){
            _set_resource_format(_data.responseJSON.result);
          }else{
            _set_resource_format('');
          }
        }
      });
    }

    function _set_resource_format(mimetype){
      let has_option_value = $(formatField).find('option[value="' + mimetype + '"]');
      if( has_option_value.length == 0 ){
        // there is no option with the guessed mimetype
        mimetype = '';
      }
      $(formatField).val(mimetype).trigger('change');
      let semantic_mimetype = mimetype.length > 0 ? mimetype : 'None';
      //TODO: French translation here??
      $(dataUploadWrapper).after('<div class="module-alert alert alert-info mrgn-tp-sm mrgn-bttm-sm canada-guess-mimetype-alert" style="margin-left: 3px;"><p>Set Resource Format to ' + semantic_mimetype + '</p></div>');
    }

    function _bind_events(){

      let urlField = $('input#field-resource-url');
      let uploadField = $('input#field-resource-upload');
      let removeButtons = $('button.btn-remove-url');

      if( removeButtons.length > 0 ){
        $(removeButtons).each(function(_index, _button){

          $(_button).off('click.reset_guessing');
          $(_button).on('click.reset_guessing', function(_event){

            $('.canada-guess-mimetype-alert').remove();
            _bind_events();

          });

        });
      }

      $(urlField).off('change.guess_mimetype');
      $(urlField).on('change.guess_mimetype', function(_event){
        $('.canada-guess-mimetype-alert').remove();
        let urlValue = $(urlField).val()
        if( urlValue.length > 0 ){
           _guess_mimetype(urlValue);
        }
      });

      $(uploadField).off('change.guess_mimetype');
      $(uploadField).on('change.guess_mimetype', function(_event){
        $('.canada-guess-mimetype-alert').remove();
        let fileName = $(uploadField).val().split(/^C:\\fakepath\\/).pop();
        if( fileName.length > 0 ){
          _guess_mimetype(fileName);
        }
      });

    }
    _bind_events();

  });
});
