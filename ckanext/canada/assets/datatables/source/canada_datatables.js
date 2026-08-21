window.addEventListener('load', function(){

  $(document).on('preInit.dt', function(_event, _settings){

    $('body.dt-view').css('visibility', 'visible');
    $('#dtprv_processing').css({
      'background-color': 'rgba(255, 255, 255, 1)',
      'display': 'block',
      'pointer-events': 'all',
    });
    $('#dtprv_processing > div').css('top', '15%');

  });

  $(document).on('init.dt', function(){

    $('#dtprv_processing').css({
      'background-color': 'rgba(255, 255, 255, 0.65)',
      'pointer-events': 'none',
    });
    $('#dtprv_processing > div').css('top', '50%');

  });

  $(document).on('processing.dt', function(_event, _settings, _processing){

    $('#dtprv_processing').css('display', _processing ? 'block' : 'none');

  });

});
