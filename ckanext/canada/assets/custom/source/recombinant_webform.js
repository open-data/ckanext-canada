window.addEventListener('load', function(){
  $(document).ready(function() {

    let select2Fields = $('.recombinant-select2');

    if( select2Fields.length > 0 ){

      $(select2Fields).each(function(_index, _field){

      // initialize select2 for recombinant-select2
      let idSuffix = $(_field).attr('id');
      $(_field).select2({});
      $(_field).parent()
               .children('#s2id_' + idSuffix)
               .addClass('conrtol-medium')
               .removeClass('form-control')
               .css({'display': 'block'});

      });

    }

  });
});
