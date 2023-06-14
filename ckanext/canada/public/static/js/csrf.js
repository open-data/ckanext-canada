$(document).ready(function(){

  let confirmActions = $("[data-module='confirm-action']");

  if( confirmActions.length > 0 ){

    $(confirmActions).each(function(){

      $(this).attr('data-module-with-data', 'true');

    });

  }

});