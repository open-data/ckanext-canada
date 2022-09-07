window.addEventListener('load', function(){
    $( document ).on( "wb-ready.wb", function( event ) {
        $('#related_pkgs ul').removeClass('list-unstyled');
        $('#related_pkgs li:gt(4)').remove();
    });
});
