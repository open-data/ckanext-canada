window.addEventListener('load', function(){
  // Add Google Analytics Custom Event Tracking to actions on the Registry
  $(document).ready(function() {
    let user, title;
    let referrer = document.referrer;

    // Get the username from the Logged In toolbar
    if( $('#usr-logged').length > 0 &&
        $('#usr-logged').find('.username').length > 0
    ){
      user = $('#usr-logged').find('.username')[0].innerText;
    }

    // Get the title from the first H1 tag
    if( $('h1').length > 0 ){
      title = $('h1')[0].innerText;
    }

    if( typeof gtag != 'undefined' ){
      // gtag function exists

      let flashes = $('.flash-messages');
      if( flashes.length > 0 &&
          flashes[0].innerText.length > 0
      ){
        // there are flash messages with content in them

        let messages = flashes[0].innerText; // get all text inside messages (excludes HTML tags)

        // track successful login
        if( messages.match(/.*now logged in.*/) ||
            messages.match(/.*est maintenant connecté.*/)
        ){

          gtag('event', 'user', {
            'action': 'Login Successful',
            'user': user,
            'title': title,
            'referrer': referrer,
            'messages': messages,
          });

        }

        // track failed login
        if( messages.match(/.*Login failed.*/) ||
            messages.match(/.*Authentification échouée.*/)
        ){

          gtag('event', 'user', {
            'action': 'Login Failed',
            'user': user,
            'title': title,
            'referrer': referrer,
            'messages': messages,
          });

        }

        // track password reset request
        if( messages.match(/.*check your e-mail inbox in order to confirm your password reset.*/) ||
            messages.match(/.*consulter votre boîte à lettres électronique pour confirmer votre demande.*/)
        ){

          gtag('event', 'user', {
            'action': 'Reset Password',
            'user': user,
            'title': title,
            'referrer': referrer,
            'messages': messages,
          });

        }

        // track account created
        if( messages.match(/.*Account Created.*/) ||
            messages.match(/.*Compte créé.*/)
        ){

          gtag('event', 'user', {
            'action': 'Request an Account',
            'user': user,
            'title': title,
            'referrer': referrer,
            'messages': messages,
          });

        }

        // track single record create for recombinant type
        if( messages.match(/.*Record Created.*/) ||
            messages.match(/.*Renregistrement créé.*/)
        ){

          gtag('event', 'recombinant', {
            'action': 'Single Record Created',
            'user': user,
            'title': title,
            'referrer': referrer,
            'messages': messages,
          });

        }

        // track single record updated for recombinant type
        if( messages.match(/.*Record.*Updated.*/) ||
            messages.match(/.*Dossier.*mis à jour.*/)
        ){

          gtag('event', 'recombinant', {
            'action': 'Single Record Updated',
            'user': user,
            'title': title,
            'referrer': referrer,
            'messages': messages,
          });

        }

        // track Excel spreadsheet uploaded for recombinant type
        if( messages.match(/.*file was successfully uploaded into the central system.*/) ||
            messages.match(/.*fichier a été téléchargé avec succès dans le système central.*/)
        ){

          gtag('event', 'recombinant', {
            'action': 'Spreadsheet Uploaded',
            'user': user,
            'title': title,
            'referrer': referrer,
            'messages': messages,
          });

        }

        // track Excel spreadsheet upload failure for recombinant type
        if( messages.match(/.*file was successfully uploaded into the central system.*/) ||
            messages.match(/.*fichier a été téléchargé avec succès dans le système central.*/)
        ){

          gtag('event', 'recombinant', {
            'action': 'Spreadsheet Upload Failed',
            'user': user,
            'title': title,
            'referrer': referrer,
            'messages': messages,
          });

        }

        // track records deleted for recombinant type
        if( messages.match(/.*[0-9]* deleted.*/) ||
            messages.match(/.*[0-9]* supprimé.*/)
        ){

          gtag('event', 'recombinant', {
            'action': 'Deleted Records',
            'user': user,
            'title': title,
            'referrer': referrer,
            'messages': messages,
          });

        }

        // track dataset created
        if( messages.match(/.*Dataset added.*/) ||
            messages.match(/.*Jeu de données ajouté.*/)
        ){

          gtag('event', 'dataset', {
            'action': 'Dataset Created',
            'user': user,
            'title': title,
            'referrer': referrer,
            'messages': messages,
          });

        }

        // track dataset updated
        if( messages.match(/.*Your dataset.*has been saved.*/) ||
            messages.match(/.*Votre jeu de données.*a été sauvegardé.*/)
        ){

          gtag('event', 'dataset', {
            'action': 'Dataset Updated',
            'user': user,
            'title': title,
            'referrer': referrer,
            'messages': messages,
          });

        }

        // track suggested dataset updated
        if( messages.match(/.*The status has been added.*/) ||
            messages.match(/.*état a été ajouté.*/)
        ){

          gtag('event', 'dataset', {
            'action': 'Suggested Dataset Updated',
            'user': user,
            'title': title,
            'referrer': referrer,
            'messages': messages,
          });

        }

        // track dataset deleted
        if( messages.match(/.*Dataset has been deleted.*/) ||
            messages.match(/.*Ce jeu de données a été supprimé.*/)
        ){

          gtag('event', 'dataset', {
            'action': 'Dataset Deleted',
            'user': user,
            'title': title,
            'referrer': referrer,
            'messages': messages,
          });

        }

        // track dataset records published by admin
        if( messages.match(/.*[0-9]* record\(s\) published.*/) ||
            messages.match(/.*[0-9]* .*enregistrements publiés.*/)
        ){

          gtag('event', 'dataset', {
            'action': 'Datasets Published by Admin',
            'user': user,
            'title': title,
            'referrer': referrer,
            'messages': messages,
          });

        }

        // track resource created
        if( messages.match(/.*Resource added.*/) ||
            messages.match(/.*Une ressource a été ajoutée.*/)
        ){

          gtag('event', 'resource', {
            'action': 'Resource Created',
            'user': user,
            'title': title,
            'referrer': referrer,
            'messages': messages,
          });

        }

        // track resource updated
        if( messages.match(/.*Your resource.*has been saved.*/) ||
            messages.match(/.*Votre ressource.*a été sauvegardée.*/)
        ){

          gtag('event', 'resource', {
            'action': 'Resource Updated',
            'user': user,
            'title': title,
            'referrer': referrer,
            'messages': messages,
          });

        }

        // track resource deleted
        if( messages.match(/.*Resource has been deleted.*/) ||
            messages.match(/.*Cette ressource a été supprimée.*/)
        ){

          gtag('event', 'resource', {
            'action': 'Resource Deleted',
            'user': user,
            'title': title,
            'referrer': referrer,
            'messages': messages,
          });

        }

      }// are there flash messages

      // track Excel template download for recombinant type
      if( $( '#xls_download' ).length > 0 ){
        $("#xls_download").on("click", function(_event){

          gtag('event', 'recombinant', {
            'action': 'Template Downloaded',
            'user': user,
            'title': title,
            'referrer': referrer,
          });

        });
      }

      // track Get Help button click
      if( $('a.get-help-analytics').length > 0 ){
        $('a.get-help-analytics').on('click', function(_event){

          gtag('event', 'user', {
            'action': 'Get Help',
            'user': user,
            'title': title,
            'referrer': referrer,
          });

        });
      }

    }// is gtag defined

  });

});
