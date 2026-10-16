window.addEventListener('load', function(){
  $(document).ready(function(){
    function unlock_account(_userName, _error, _element){
      $.ajax({
        'url': '/api/action/security_throttle_user_reset',
        'type': 'POST',
        'dataType': 'JSON',
        'data': {
          'user': _userName,
        },
        'complete': function(_data){
          if( _data.responseJSON ){  // we have response JSON
            if( _data.responseJSON.success ){  // successful format guess
              if( _data.responseJSON.result.count == 0 ){
                $(_element).off('click.unlockAccount');
                $(_element).off('keyup.unlockAccount');
                $(_element).parent().removeClass('text-warning').addClass('text-success');
                $(_element).parent().html('<span class="fa fa-unlock">&nbsp;</span>');
              }
            }else{  // validation error
              alert(_error);
            }
          }else{  // fully flopped ajax request
            alert(_error);
          }
        }
      });
    }
    let lockButtons = $('.canada-security-unlock');
    if( lockButtons.length > 0 ){
      $(lockButtons).each(function(_index, _button){
        let userName = $(_button).attr('data-user');
        let error = $(_button).attr('data-error');
        if( userName.length > 0 ){
          $(_button).off('click.unlockAccount');
          $(_button).off('keyup.unlockAccount');
          $(_button).on('click.unlockAccount', function(_event){
            unlock_account(userName, error, _button);
          });
          $(_button).on('keyup.unlockAccount', function(_event){
            let keyCode = _event.keyCode ? _event.keyCode : _event.which;
            // enter key required for a11y
            if( keyCode == 13 ){
              unlock_account(userName, error, _button);
            }
          });
        }
      });
    }
  });
});
