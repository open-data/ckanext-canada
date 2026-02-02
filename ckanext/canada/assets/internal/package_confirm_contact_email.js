ckan.module('package_confirm_contact_email', function($){
  return {
    initialize: function () {
      function _showModal(){
        $('#confirm-contact-email.modal').attr('aria-hidden', false);
        $('#confirm-contact-email.modal').attr('tabindex', 0);
        $('#confirm-contact-email.modal').show();
      }

      function _hideModal(){
        $('#confirm-contact-email.modal').attr('aria-hidden', true);
        $('#confirm-contact-email.modal').attr('tabindex', -1);
        $('#confirm-contact-email.modal').hide();
      }

      // Add a click event listener to the go-back-email button
      $('#go-back-email').on('click', function(_event){
        _hideModal();
        $('#field-maintainer_email').focus();
        _event.preventDefault();
        _event.stopPropagation();
      });

      // Add a click event listener to the continue-submit button
      $('#continue-submit').on('click', function(_event){
        $('<input />').attr('type', 'hidden')
                      .attr('name', 'save')
                      .attr('value', true)
                      .appendTo('#dataset-edit');
        $('#dataset-edit').submit();
      });

      $('#confirm-contact-email-dismiss').on('click', function(_event){
        _hideModal();
        _event.preventDefault();
        _event.stopPropagation();
      });

      $('#confirm-contact-email').on('click', function(_event){
        _hideModal();
        _event.preventDefault();
        _event.stopPropagation();
      });

      $('#confirm-contact-email .modal-content').on('click', function(_event){
        _event.preventDefault();
        _event.stopPropagation();
      });

      // Add a click event listener to the save button
      $("#dataset-edit .form-actions button[type='submit'][name='save']").click(function(_event){
        if( typeof $('#field-maintainer_email') == 'undefined' ||
            typeof $('#field-maintainer_email').val() == 'undefined' ||
            $('#field-maintainer_email').val().trim() === ''
        ){
          _event.preventDefault();
          _event.stopPropagation();
          _showModal();
          return false;
        }
      });
    }
  };
});
