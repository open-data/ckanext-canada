document.addEventListener('click', function(_event){
    const link = _event.target.closest('a');
    if( ! link || ! link.href ){
      return;
    }
    const targetUrl = link.href;
    const target = link.target;
    const url = new URL(targetUrl, window.location.href);
    if( url.origin === window.location.origin ){
      return;
    }
    if( url.protocol === 'javascript:' ){
      return;
    }
    const trustedDomains = [
      'canada.ca',
      'gc.ca',
    ];
    const isTrusted = trustedDomains.some(function(_domain){
      return (url.hostname === _domain || url.hostname.endsWith('.' + _domain));
    });
    if( isTrusted ){
      return;
    }
    _event.preventDefault();
    _event.stopImmediatePropagation();
    const language = document.documentElement.lang || 'en';
    const modal = document.createElement('div');
    modal.className = 'modal show';
    modal.id = 'canada-external-site-warning';
    modal.setAttribute('tabindex', 0);
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-hidden', false);
    modal.setAttribute('aria-modal', true);
    modal.setAttribute('aria-labelledby', 'canada-external-site-warning--label');
    modal.setAttribute('style', 'background: rgba(0, 0, 0, 0.15) !important;');
    const modalTitle = language === 'fr' ? 'Quitter le site' : 'Leaving Site';
    const modalLeadingContent = language === 'fr' ? 'Vous êtes sur le point de quitter le site web Canada.ca. Ce lien vous dirigera vers un site externe non gouvernemental.' : 'You are about to leave the Canada.ca website and access a site that is not affiliated with the Government of Canada.';
    const modelContent = language === 'fr' ? "Le gouvernement du Canada n'est pas responsable de l'exactitude, de l'actualité, ni de la fiabilité du contenu de ce site externe. Il se peut également que ce dernier ne soit pas assujetti à la <em>Loi sur les langues officielles,</em> à la <em>Loi sur la protection des renseignements personnels,</em> ni à la <em>Loi canadienne sur l'accessibilité.</em>" : 'The Government of Canada is not responsible for the accuracy, timeliness or reliability of the content of this external site. This site may not be subject to the <em>Official Languages Act,</em> the <em>Privacy Act,</em> or the <em>Accessible Canada Act.</em>';
    const cancelButtonLabel = language === 'fr' ? 'Annuler' : 'Cancel';
    const confirmButtonLabel = language === 'fr' ? 'Quitter le site' : 'Leave Site';
    modal.innerHTML = '<div style="display: inline-block; height: 100%; vertical-align: middle;"></div><div class="modal-dialog" style="display: inline-block; text-align: left; vertical-align: middle;"><div class="modal-content" style="border: 1px solid rgba(0, 0, 0, 0.2); border-radius: 6px;"><div class="modal-header" style="background-color: #2e5274; display: flex; align-items: center; justify-content: space-between;"><h3 class="modal-title" style="color: white; margin: 0;" id="canada-external-site-warning--label"><span class="fa fa-warning" aria-hidden="true"></span>&nbsp;&nbsp;' + modalTitle + '</h3><button type="button" class="btn-close" style="background-color: transparent; background-position: center; background-repeat: no-repeat; background-image: url(\'/data/static/img/data_img/modal-close.svg\'); padding: 0.5rem 0.5rem; margin-left: auto; border: 0; opacity: 0.5; width: 1em; height: 1em;" id="canada-external-site-warning--dismiss" aria-label="Close"></button></div><div class="modal-body"><p><strong>' + modalLeadingContent + '</strong></p><p>' + modelContent + '</p></div><div class="modal-footer"><button class="btn btn-sm btn-secondary" id="canada-external-site-warning--cancel">' + cancelButtonLabel + '</button><button class="btn btn-sm btn-warning" id="canada-external-site-warning--continue">' + confirmButtonLabel + '</button></div></div></div>';
    document.body.append(modal);
    modal.querySelector('#canada-external-site-warning--cancel').focus();
    modal.querySelector('#canada-external-site-warning--continue').addEventListener('click', function(){
      modal.remove();
      if( target === '_blank' ){
        window.open(targetUrl, '_blank', 'noopener,noreferrer');
      }else{
        window.location.href = targetUrl;
      }
      _event.target.focus();
    });
    modal.querySelector('#canada-external-site-warning--cancel').addEventListener('click', function(){
      modal.remove();
      _event.target.focus();
    });
    modal.querySelector('#canada-external-site-warning--dismiss').addEventListener('click', function(){
      modal.remove();
      _event.target.focus();
    });
});
