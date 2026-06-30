this.ckan.module('canada-user-opt-in-feature', function($){
  return {
    /* options object can be extended using data-module-* attributes */
    options: {
      csrf_name: null,
      csrf_value: null,
      page_redirect: null,
      label: null,
      button_label: null,
      user_id: null,
      feature_key: null,
      feature_value: true,
    },
    initialize: function (){
      _load_user_opt_in(this);
    }
  };
});

function _load_user_opt_in(CKAN_MODULE){
  const _ = CKAN_MODULE._;
  const csrfTokenName = CKAN_MODULE.options.csrf_name;
  const csrfTokenValue = CKAN_MODULE.options.csrf_value;
  const pageRedirect = CKAN_MODULE.options.page_redirect;
  const label = CKAN_MODULE.options.label;
  const buttonLabel = CKAN_MODULE.options.button_label;
  const userID = CKAN_MODULE.options.user_id;
  const featureKey = CKAN_MODULE.options.feature_key;
  const featureValue = CKAN_MODULE.options.feature_value;

  let postData = {'id': userID};
  postData[featureKey] = featureValue;
  postData[csrfTokenName] = csrfTokenValue;

  let container = $('[data-module="canada-user-opt-in-feature"][data-module-feature_key="' + featureKey + '"]');
  let htmlContent = '<div class="alert alert-warning"><p>' + label + '</p><p><a role="button" class="btn btn-primary btn-small" href="javascript:void(0);">' + buttonLabel + '</a></p></div>';

  function _render_failure(_consoleMessage, _message, _type){
    console.warn(_consoleMessage);
    $(container).find('#uoif_failure_message').remove();
    $(container).append('<div id="uoif_failure_message" class="alert alert-dismissible show alert-' + _type + '"><p>' + _message + '</p></div>');
  }

  if( $(container).children('.alert').length == 0 ){
    $(container).append(htmlContent);
    let button = $(container).find('a.btn');
    if( button.length > 0 ){
      $(button).off('click.optInFeature');
      $(button).on('click.optInFeature', function(_event){
        $(button).addClass('disabled');
        $(button).attr('disabled', 'disabled');
        $.ajax({
        'url': '/api/action/user_patch',
        'type': 'POST',
        'dataType': 'JSON',
        'data': postData,
        'complete': function(_data){
          if( _data.responseJSON ){  // we have response JSON
            if( _data.responseJSON.success ){  // successful patch
              if(
                _data.responseJSON.result.plugin_extras &&
                typeof _data.responseJSON.result.plugin_extras == 'object' &&
                ! Array.isArray(_data.responseJSON.result.plugin_extras) &&
                _data.responseJSON.result.plugin_extras[featureKey] == featureValue
              ){
                if( pageRedirect && pageRedirect.startsWith('#') ){
                  window.location.hash = pageRedirect.replace('#', '');
                  window.location.reload();
                  return;
                }else if( pageRedirect ){
                  window.location.href = pageRedirect;
                  return;
                }
                window.location.reload();
                return;
              }else{  // unexpected return dict
                _render_failure('Opt-in Feature — Unexpected response data.', _('Failed to change user settings'), 'danger');
                console.warn(_data.responseJSON);
              }
            }else{  // validation error
              _render_failure('Opt-in Feature — ValidationError exception was raised.', _('Failed to change user settings'), 'danger');
              console.warn(_data.responseJSON);
            }
          }else{  // fully flopped ajax request
            _render_failure('Opt-in Feature — Failed to gather a JSON response.', _('Failed to change user settings'), 'danger');
          }
        }
      });
      });
    }
  }
}
