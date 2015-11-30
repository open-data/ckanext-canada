$(document).on("pageinit", function()
  {
    var $table = $('#dtprv');
    var poll = setInterval( function(){
      if ($.fn.DataTable) {
        $table.dataTable($.extend($table.data('wet-boew'), {bDestroy:true}));
        clearInterval(poll);
      }
    }, 100 );
  }
);
