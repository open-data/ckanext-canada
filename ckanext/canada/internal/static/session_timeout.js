/*
 Show popup when sesion times out
 */
$(document).ready(function() {
    setTimeout(function(){
        $( document ).trigger( "open.wb-lbx", [
            [
                {
                    src: "#timeout",
                    type: "inline"
                }
            ]
        ]);
    }, 5000);
});