function load_voting_scripts(){

    var votingWrapper = document.getElementById('voting-wrapper');
    var hasLoadedVotingScripts = false;

    if( typeof votingWrapper != "undefined" && votingWrapper != null ){

      if( ! votingWrapper.classList.contains('canada-voting-fix-hide') ){
        votingWrapper.classList.add('canada-voting-fix-hide');
      }

      const cacheVersion = 1

      const votingScripts = [
        'https://cdn.jsdelivr.net/gh/gjunge/rateit.js@1.1.2/scripts/jquery.rateit.min.js',
        '/modules/contrib/webform/js/webform.element.rating.js?cv=' + cacheVersion
      ];

      const votingStyles = [
        '/profiles/og/modules/custom/voting_webform/css/rating.css?cv=' + cacheVersion,
        'https://cdn.jsdelivr.net/gh/gjunge/rateit.js@1.1.2/scripts/rateit.css',
        '/modules/contrib/webform/css/webform.element.rating.css?cv=' + cacheVersion
      ];

      function insert_voting_scripts(){

        setTimeout(function(){

          if( hasLoadedVotingScripts ){ return; }

          const scriptElement = document.querySelector('script[nonce]');
          const nonceValue = scriptElement.nonce;

          if( votingWrapper.getElementsByTagName('form').length == 0 ){ return; }

          votingScripts.forEach(function(_scriptSource){

            var script = document.createElement('script');
            script.type = 'text/javascript';
            script.src = _scriptSource;
            script.setAttribute('nonce', nonceValue);
            document.head.appendChild(script);

          });

          votingStyles.forEach(function(_styleSource){

            var link = document.createElement('link');
            link.rel = 'stylesheet';
            link.media = 'all';
            link.href = _styleSource;
            link.setAttribute('nonce', nonceValue);
            document.head.appendChild(link);

          });

          hasLoadedVotingScripts = true;

          if( ! votingWrapper.classList.contains('og-fade-in') ){
            votingWrapper.classList.add('og-fade-in');
          }
          if( votingWrapper.classList.contains('canada-voting-fix-hide') ){
            votingWrapper.classList.remove('canada-voting-fix-hide');
          }
          if( ! votingWrapper.classList.contains('canada-voting-fix-show') ){
            votingWrapper.classList.add('canada-voting-fix-show');
          }

          observer.disconnect();

        },750);

        //fallback if 750ms was not enough time for the form to be inserted into the dom tree
        setTimeout(function(){

          if( ! votingWrapper.classList.contains('og-fade-in') ){
            votingWrapper.classList.add('og-fade-in');
          }
          if( votingWrapper.classList.contains('canada-voting-fix-hide') ){
            votingWrapper.classList.remove('canada-voting-fix-hide');
          }
          if( ! votingWrapper.classList.contains('canada-voting-fix-show') ){
            votingWrapper.classList.add('canada-voting-fix-show');
          }

        },1500);

      }

      const observer = new MutationObserver(function(_mutations){

        _mutations.forEach(function(_mutation){

          var attributeValue = _mutation.target.getAttribute(_mutation.attributeName);

          if( attributeValue.includes('wb-data-ajax-replace-inited') ){

            insert_voting_scripts();

          }

        });

      });

      observer.observe(votingWrapper, {
        attributes: true,
        attributeFilter: ['class']
      });

    }

}

load_voting_scripts();