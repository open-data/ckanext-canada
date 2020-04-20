/*
 Add Google Analytics Event Tracking to actions on the Registry
 */
window.onload = function() {
  let flashes = document.getElementsByTagName('aside');
  if (flashes && flashes[0].innerText) {
    let msg = flashes[0].innerText;

    // track successful login
    if (msg.match(/.*now logged in$/) || msg.match(/.*est maintenant connecté$/))
      ga('send', 'event', 'Login', msg, document.referrer);

    // track password reset request
    if (msg == 'Please check your e-mail inbox in order to confirm your password reset request.' ||
        msg == 'S.V.P. consulter votre boîte à lettres électronique pour confirmer votre demande de réinitialisation.')
      ga('send', 'event', 'Login', 'Reset password', document.location.href);

    // track account created
    if (msg.match(/^Account Created.*/) || msg.match(/^Compte créé.*/))
      ga('send', 'event', 'Login', 'Request an Account', document.referrer);

    // track single record create for recombinant type
    if (msg == 'Record Created')
      ga('send', 'event', document.getElementsByTagName('H1')[0].innerText, msg, document.location.href);

    // track single record updated for recombinant type
    if (msg.match(/^Record.*Updated$/))
      ga('send', 'event', document.getElementsByTagName('H1')[0].innerText, msg, document.location.href);

    // track Excel spreadsheet uploaded for recombinant type
    if (msg == 'Your file was successfully uploaded into the central system.' ||
        msg == 'Votre fichier a été téléchargé avec succès dans le système central.')
      ga('send', 'event', document.getElementsByTagName('H1')[0].innerText, 'Spreadsheet uploaded', document.location.href);
  }

  // track invlid login
  if (document.getElementById('login-invalid'))
    ga('send', 'event', 'Login', 'Invalid login', document.location.href);

  // track Excel spreadsheet uploaded errors for recombinant type
  if (document.getElementById('upload-errors')) {
    let msg = document.getElementById('upload-errors').innerText;
    if (msg)
      ga('send', 'event', document.getElementsByTagName('H1')[0].innerText, 'Spreadsheet upload errored ' + msg, document.location.href);
  }
};
