function load_voting_scripts(){

    var votingWrapper = document.getElementById('voting-wrapper');
    var hasLoadedVotingScripts = false;

    if( typeof votingWrapper !== "undefined" ){

      votingWrapper.style.opacity = 0;
      votingWrapper.style.pointerEvents = 'none';

      const votingScripts = [
        'https://cdn.jsdelivr.net/gh/gjunge/rateit.js@1.1.2/scripts/jquery.rateit.min.js',
        '/modules/contrib/webform/js/webform.element.rating.js?v=8.7.5'
      ];

      const votingStyles = [
        '/profiles/og/modules/custom/voting_webform/css/rating.css',
        'https://cdn.jsdelivr.net/gh/gjunge/rateit.js@1.1.2/scripts/rateit.css',
        '/modules/contrib/webform/css/webform.element.rating.css'
      ];

      function insert_voting_scripts(){

        setTimeout(function(){

          if( hasLoadedVotingScripts ){ return; }

          if( votingWrapper.getElementsByTagName('form').length == 0 ){ return; }

          votingScripts.forEach(function(_scriptSource){

            var script = document.createElement('script');
            script.type = 'text/javascript';
            script.src = _scriptSource;
            document.head.appendChild(script);

          });

          votingStyles.forEach(function(_styleSource){

            var link = document.createElement('link');
            link.rel = 'stylesheet';
            link.media = 'all';
            link.href = _styleSource;
            document.head.appendChild(link);

          });

          hasLoadedVotingScripts = true;

          votingWrapper.classList.add('og-fade-in');
          votingWrapper.style.pointerEvents = 'all';

        },750);

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