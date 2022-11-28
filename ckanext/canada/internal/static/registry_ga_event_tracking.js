window.addEventListener('load', function(){
  /*
  Add Google Analytics Event Tracking to actions on the Registry
  */
  $(document).ready(function() {
    let user, title;
    if ($( '.username' ).length)
      user = ' by ' + $( '.username' )[0].innerText;
    if ($( 'h1' ).length)
      title = $( 'h1' )[0].innerText;

    let flashes = $( 'aside' );
    if (flashes.length && flashes[0].innerText) {
      let msg = flashes[0].innerText;

      // track successful login
      if (msg.match(/.*now logged in$/) || msg.match(/.*est maintenant connecté$/))
        ga('send', 'event', 'Login', msg, document.referrer);

      // track password reset request
      if (msg == 'Please check your e-mail inbox in order to confirm your password reset request.' ||
          msg == 'S.V.P. consulter votre boîte à lettres électronique pour confirmer votre demande de réinitialisation.')
        ga('send', 'event', 'Login', 'Reset password', document.referrer);

      // track account created
      if (msg.match(/^Account Created.*/) || msg.match(/^Compte créé.*/))
        ga('send', 'event', 'Login', 'Request an Account', document.referrer);

      // track single record create for recombinant type
      if (msg == 'Record Created')
        ga('send', 'event', title, msg + user, document.location.href);

      // track single record updated for recombinant type
      if (msg.match(/^Record.*Updated$/))
        ga('send', 'event', title, msg + user, document.referrer);

      // track Excel spreadsheet uploaded for recombinant type
      if (msg == 'Your file was successfully uploaded into the central system.' ||
          msg == 'Votre fichier a été téléchargé avec succès dans le système central.')
        ga('send', 'event', title, 'Spreadsheet uploaded' + user, document.location.href);

      // track records deleted for recombinant type
      if (msg.match(/^[0-9]* deleted.$/))
        ga('send', 'event', title, msg + user, document.referrer);

      // track dataset created
      if (msg.match(/Your record.*has been saved/))
        ga('send', 'event', 'Dataset', 'Dataset added' + user, document.location.href);

      // TO-DO
      // track dataset updated
      // no status message provided by controller
      // update when controller provides status message

      // track dataset records published by admin
      if (msg.match(/^[0-9]* record\(s\) published.$/))
        ga('send', 'event', 'Dataset', msg + user, document.referrer);

      // track dataset deleted
      if (msg == 'Record has been deleted.' || msg == 'L\'ensemble de données a été supprimé.')
        ga('send', 'event', 'Dataset', 'Dataset deleted' + user, document.referrer);

      // track resource created
      if (msg.match(/A resource has been added/) || msg.match(/Une ressource a été ajoutée/))
        ga('send', 'event', 'Dataset', 'Resource or related item added' + user, document.location.href);

      // track resource updated
      if (msg == 'Resource updated.')
        ga('send', 'event', 'Dataset', 'Resource or related item updated' + user, document.referrer);

      // track resource deleted
      if (msg == 'Resource has been deleted.' || msg == 'Cette ressource a été supprimée.')
        ga('send', 'event', 'Dataset', 'Resource or related item deleted' + user, document.referrer);
    }

    // track invalid login
    if ($( '#login-invalid' ).length)
      ga('send', 'event', 'Login', 'Invalid login', document.location.href);

    // track Excel spreadsheet uploaded errors for recombinant type
    if ($( '#upload-errors' ).length && $( '#upload-errors' )[0].innerText)
        ga('send', 'event', title, 'Spreadsheet upload errored ' + $( '#upload-errors' )[0].innerText + user, document.location.href);

    // track Excel template download for recombinant type
    if ($( '#xls_download' ).length) {
      $("#xls_download").on("click", function () {
        ga('send', 'event', title, 'Template Downloaded by ' + user, this.href);
      });
    }
  });
});
