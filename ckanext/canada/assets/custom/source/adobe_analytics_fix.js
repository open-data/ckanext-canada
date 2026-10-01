// NOTE: Adobe Analytics sets a cookie called clickURL.
//       This can have javascript inside of it, we need to sanitize that!
function canada_fix_adobe_analytics_cookies(){
  const maxTries = 20;
  let currentTry = 0;
  let interval = false;

  function _fix_adobe_analytics_cookies(){
    if( currentTry > maxTries ){
      clearInterval(interval);
      interval = false;
      return;
    }

    currentTry++;

    if( typeof _satellite == 'undefined' || typeof _satellite.cookie == 'undefined' || typeof _satellite.cookie.set == 'undefined' ){
      return;
    }

    clearInterval(interval);
    interval = false;

    const superFunc = _satellite.cookie.set;
    _satellite.cookie.set = function(_t, _n, _i){
      if( _t != 'clickURL' || ! _n.toString().includes('javascript') ){
        return superFunc(_t, _n, _i);
      }
      return superFunc(_t, '', _i);
    }
  }

  interval = setInterval(_fix_adobe_analytics_cookies, 100);
}

canada_fix_adobe_analytics_cookies();
