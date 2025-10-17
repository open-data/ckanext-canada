window.addEventListener('load', function(){
  $(document).ready(function(){
    const maxTries = 10;
    let reportWrapper = $('.frictionless-components-report');
    let tries = 0;
    function expand_reports(_wrapper){
      let errorToggles = $(_wrapper).find('a.badge.collapsed');
      let errorSections = $(_wrapper).find('div.collapse');
      if( errorToggles.length > 0 && errorSections.length > 0 ){
        $(errorToggles).each(function(_index, _errorToggle){
          $(errorSections).eq(_index).attr('id', 'validation-error-' + _index).collapse('show');
          $(_errorToggle).attr('data-bs-toggle', 'collapse')
                         .attr('data-toggle', null)
                         .attr('aria-controls', 'validation-error-' + _index)
                         .removeClass('collapsed')
                         .attr('aria-expanded', 'true');
          $(_errorToggle).off('click');
          $(_errorToggle).on('click', function(_event){
            _event.stopPropagation();
            _event.stopImmediatePropagation();
            _event.preventDefault();
            if( ! $(_errorToggle).hasClass('collapsed') ){
              $(errorSections).eq(_index).collapse('hide');
              $(_errorToggle).addClass('collapsed')
                             .attr('aria-expanded', 'false');
            }else{
              $(errorSections).eq(_index).collapse('show');
              $(_errorToggle).removeClass('collapsed')
                             .attr('aria-expanded', 'true');
            }
          });
        });
      }
    }
    let trier = setInterval(function(){
      reportWrapper = $('.frictionless-components-report');
      if( tries >= maxTries || reportWrapper.length > 0 ){
        if( reportWrapper.length > 0 ){
          expand_reports(reportWrapper);
        }
        clearInterval(trier);
        trier = false;
        return;
      }
      tries++;
    }, 250);
  });
});