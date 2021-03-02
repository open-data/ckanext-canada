/*
 Show popup when sesion times out
 */
function timeoutPop(time) {
    setTimeout(function(){
        $( document ).trigger( "open.wb-lbx", [
            [
                {
                    src: "#timeout",
                    type: "inline"
                }
            ]
        ]);
    }, time*1000);
}
