ckan.module('package_confirm_contact_email', function ($) {
  return {
    initialize: function () {
      console.log('Package form JS loaded');

      // Add a click event listener to the go-back-email button
      $('#go-back-email').click(function() {
        $('#field-maintainer_email').focus();

      });

      // Add a click event listener to the continue-submit button
      $('#continue-submit').click(function() {
        $('#dataset-edit').submit();
      });

      // Add a click event listener to the save button
      $("#saveBtn").click(function() {
        if ($('#field-maintainer_email').val().trim() === '') {
          $('#confirm-contact-email').modal('show');
        }
        return false;
      });

    }
  };
});
