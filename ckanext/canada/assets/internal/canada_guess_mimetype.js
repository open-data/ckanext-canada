window.addEventListener('load', function(){
  $(document).ready(function() {

    const lang = $('html').attr('lang').length > 0 ? $('html').attr('lang') : 'en';

    // slightly different error messages for the front-end users.
    // as the UX is different than the API users.
    let failedGuessErrorMessage = 'Could not determine a resource format. Please supply a format below.';
    let failedChoicesErrorMessage = 'Could not determine a valid resource format. Please supply a different format below.';
    if( lang == 'fr' ){
      //TODO: set french error messages
    }

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

    function _set_success_message(format){
      let message = 'Set Resource Format to <strong>' + format + '</strong>';
      if( lang == 'fr' ){
        //TODO: set french message
      }
      $(dataUploadWrapper).after('<div class="module-alert alert alert-info mrgn-tp-sm mrgn-bttm-sm canada-guess-mimetype-alert" style="margin-left: 3px;"><p>' + message + '</p></div>');
    }

    function _set_warning_message(error){
      $(dataUploadWrapper).after('<div class="module-alert alert alert-danger mrgn-tp-sm mrgn-bttm-sm canada-guess-mimetype-alert" style="margin-left: 3px;"><p>' + error + '</p></div>');
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
          if( _data.responseJSON ){  // we have response JSON
            if( _data.responseJSON.success ){  // successful format guess
              _set_resource_format(_data.responseJSON.result);
            }else{  // validation error
              _set_resource_format('');
              _set_warning_message(failedGuessErrorMessage);
            }
          }else{  // fully flopped ajax request
            _set_resource_format('');
            _set_warning_message(failedGuessErrorMessage);
          }
        }
      });
    }

    function _set_resource_format(mimetype){
      let has_option_value = $(formatField).find('option[value="' + mimetype + '"]');
      if( has_option_value.length == 0 ){
        // there is no option with the guessed mimetype
        // we can assume that the format is not in scheming choices
        // for the front-end here.
        mimetype = '';
        // we have a different message here for the front-end, because
        // API users will need the full list of choices, but the front-end
        // users will have the select2 field to choose from.
        _set_warning_message(failedChoicesErrorMessage);
      }
      $(formatField).val(mimetype).trigger('change');
      if( mimetype.length > 0 ){
        _set_success_message(mimetype);
      }
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

          $(_button).off('keyup.reset_guessing');
          $(_button).on('keyup.reset_guessing', function(_event){

            let keyCode = _event.keyCode ? _event.keyCode : _event.which;

            // space and enter keys required for a11y
            if( keyCode == 32 || keyCode == 13 ){

              $('.canada-guess-mimetype-alert').remove();
              _bind_events();

            }

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
