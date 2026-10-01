window.addEventListener('load', function(){
  $(document).ready(function() {

    const lang = $('html').attr('lang').length > 0 ? $('html').attr('lang') : 'en';
    const ds_formats = ['csv', 'tsv'];

    let dataUploadWrapper = $('.resource-upload-field.form-group');

    let rtypeField = $('#field-resource_type');
    let charsetField = $('#field-character_set');
    let formatField = $('#field-format');
    const currentFormat = $(formatField).val();
    if ( formatField.length > 0 ){

      // initialize select2 for the Resource Format field
      $(formatField).select2({});
      $(formatField).parent()
                    .children('#s2id_field-format')
                    .addClass('conrtol-medium')
                    .removeClass('form-control')
                    .removeClass('form-select')
                    .css({'display': 'block'});

    }

    let urlTypeField = $('#resource-url-upload');
    const isUploadType = typeof urlTypeField != 'undefined' && urlTypeField.length > 0 ? $(urlTypeField).is(':checked') : false;

    if ( ! isUploadType && typeof currentFormat != 'undefined' && currentFormat.length > 0 && ds_formats.includes(currentFormat.toLowerCase()) ){
      _set_datastore_alert_message(currentFormat);
    }

    function _set_datastore_alert_message(format){
      let message = 'You are linking to an external <strong>' + format + '</strong> file. To access full validation and <span class="canada-cursor-help" title="Application Programming Interface" aria-label="Application Programming Interface">API</span> features, upload it directly to the Registry. Your data will be validated for errors, loaded into a dedicated database table, and accessible via the <span class="canada-cursor-help" title="Application Programming Interface" aria-label="Application Programming Interface">API.</span> This will make your data simpler to manage, access, reuse, and share with other tools and systems.';
      if( lang == 'fr' ){
        message = 'Vous avez créé un lien vers un fichier <strong>' + format + '</strong> externe. Pour avoir accès à toutes les fonctionnalités de validation et d\'intégration d\'une <span class="canada-cursor-help" title="Interface de programmation d\'applications" aria-label="Interface de programmation d\'applications">API,</span> téléversez le fichier directement dans le Registre. Vos données seront validées pour détecter les erreurs, chargées dans une table de base de données qui leur est destinée et accessibles au moyen de <span class="canada-cursor-help" title="Interface de programmation d\'applications" aria-label="Interface de programmation d\'applications">l\'API.</span> Vos données seront ainsi plus faciles à gérer, à consulter, à réutiliser et à partager avec d\'autres outils et systèmes.';
      }
      $(dataUploadWrapper).after('<div class="module-alert alert alert-guidance mrgn-tp-sm mrgn-bttm-sm canada-link-ds-upload-alert" style="margin-left: 3px;"><p>' + message + '</p></div>');
    }

    function _set_success_message(format){
      let message = 'Set Resource Format to <strong>' + format + '</strong>';
      if( lang == 'fr' ){
        message = 'Établissez le format de la ressource à <strong>' + format + '</strong>';
      }
      $(dataUploadWrapper).after('<div class="module-alert alert alert-info mrgn-tp-sm mrgn-bttm-sm canada-guess-mimetype-alert" style="margin-left: 3px;"><p>' + message + '</p></div>');
    }

    function _clear_alerts(){
      $('.canada-guess-mimetype-alert').remove();
      $('.canada-link-ds-upload-alert').remove();
    }

    function _guess_mimetype(url, _is_upload_field){
      let tokenFieldName = $('meta[name="csrf_field_name"]').attr('content');
      let tokenValue = $('meta[name="' + tokenFieldName + '"]').attr('content');
      payload = {'url': url};
      payload[tokenFieldName] = tokenValue;
      $.ajax({
        'url': '/api/action/canada_guess_mimetype',
        'type': 'POST',
        'dataType': 'JSON',
        'data': payload,
        'complete': function(_data){
          if( _data.responseJSON ){  // we have response JSON
            if( _data.responseJSON.success ){  // successful format guess
              _set_resource_format(_data.responseJSON.result);
              if ( ! _is_upload_field && ds_formats.includes(_data.responseJSON.result.toLowerCase()) ){
                _set_datastore_alert_message(_data.responseJSON.result);
              }
            }else{  // validation error
              _set_resource_format('');
            }
          }else{  // fully flopped ajax request
            _set_resource_format('');
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
      }
      $(formatField).val(mimetype).trigger('change');
      if( mimetype.length > 0 ){
        _set_success_message(mimetype);
      }
    }

    function _set_tabledesigner_related_fields(){
      // explicitly set type to dataset and charset to UTF-8 and format to CSV
      // for TableDesigner Resources.
      $(charsetField).val('UTF-8').trigger('change');
      $(rtypeField).val('dataset').trigger('change');
      _set_resource_format('CSV');
    }

    function _bind_events(){

      let urlField = $('input#field-resource-url');
      let uploadField = $('input#field-resource-upload');
      let tableDesignerButton = $('button#resource-table-designer-button');
      let removeButtons = $('button.btn-remove-url');

      if( removeButtons.length > 0 ){
        $(removeButtons).each(function(_index, _button){

          $(_button).off('click.reset_guessing');
          $(_button).on('click.reset_guessing', function(_event){

            _clear_alerts();
            _bind_events();

          });

          $(_button).off('keyup.reset_guessing');
          $(_button).on('keyup.reset_guessing', function(_event){

            let keyCode = _event.keyCode ? _event.keyCode : _event.which;

            // space and enter keys required for a11y
            if( keyCode == 32 || keyCode == 13 ){

              _clear_alerts();
              _bind_events();

            }

          });

        });
      }

      $(urlField).off('change.guess_mimetype');
      $(urlField).on('change.guess_mimetype', function(_event){
        _clear_alerts();
        let urlValue = $(urlField).val()
        if( urlValue.length > 0 ){
           _guess_mimetype(urlValue, false);
        }
      });

      $(uploadField).off('change.guess_mimetype');
      $(uploadField).on('change.guess_mimetype', function(_event){
        _clear_alerts();
        const selectedFile = _event.target.files[0];
        let fileName = '';
        if( selectedFile ){
          fileName = selectedFile.name;
        }
        if( fileName.length > 0 ){
          _guess_mimetype(fileName, true);
        }
      });

      $(tableDesignerButton).off('click.set_mimetype');
      $(tableDesignerButton).on('click.set_mimetype', function(_event){
        _clear_alerts();
        _set_tabledesigner_related_fields();
      });

      $(tableDesignerButton).off('keyup.set_mimetype');
      $(tableDesignerButton).on('keyup.set_mimetype', function(_event){
        let keyCode = _event.keyCode ? _event.keyCode : _event.which;
        // space and enter keys required for a11y
        if( keyCode == 32 || keyCode == 13 ){
          _clear_alerts();
          _set_tabledesigner_related_fields();
        }
      });

    }
    _bind_events();

  });
});
