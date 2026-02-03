/*
 * Copies of strings that need translations
 * in CKAN translation js building
 *
 * NOTE: CKAN builds JS i18n files off of .js file occurances
 *       from the POT files. So they need to exist in JS extractions.
**/

const _ = function(x){ return x; }

_('Requesting Download...')  // promise-download js module
_('Downloads')  // promise-download js module
_('You have unfinished downloads in this page. Do you want to stop these downloads and leave the page?')  // promise-download js module
_('Downloading file...')  // promise-download js module
_('Successfully downloaded file')  // promise-download js module
_('Error downloading file, trying again through your browser')  // promise-download js module
_('Searching...')  // autocomplete js module // TODO: remove after upstream contrib
_('Saved new order')  // resource-reorder js module // TODO: remove after upstream contrib
