
$( document ).on( "wb-ready.wb", function( event ) {
    $('#related_pkgs ul').removeClass('list-unstyled');
    $('#related_pkgs li:gt(4)').remove();

    var listItems = $("#related_pkgs a");
    listItems.each(function(idx, a) {
        var text = $(a).text().trim();
        if (text.length > 180) {
            $(a).text(text.substring(0,175) + '...');
        }
    });
});
