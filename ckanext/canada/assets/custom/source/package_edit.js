window.addEventListener('load', function(){
  $(document).ready(function() {
    // late init for date polyfill on scheming subforms
    $('fieldset[name=scheming-repeating-subfields]').on('scheming.subfield-group-init', function() {
      $(this).find('div.scheming-subfield-group').last()
          .find('span.wb-date-wrap.input-group').each(function(i, obj) {
        // discard broken polyfill
        var $clean = $(obj).clone().find('input').first()
          .removeClass('wb-init wb-date-inited picker-field');
        $(obj).replaceWith($clean);
      });
      // reapply polyfills, make sure to use wet's jQuery object
      $wetjq('input[type=date]').trigger('wb-init.wb-date');
    });
  });
});
