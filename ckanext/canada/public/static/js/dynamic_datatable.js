$(document).on("pageinit", function()
  {
    var $table = $('#dtprv');
    var poll = setInterval( function(){
      if ($.fn.DataTable) {
        $table.dataTable($.extend($table.data('wet-boew'), {
          bDestroy:true,
          fnDrawCallback: function(oSettings){
            // http://stackoverflow.com/questions/16917605/jquerymobilerefresh-after-dynamically-adding-rows-to-a-table-with-column-toggle
            var columnIndex = 0;
            $("#dtprv-popup fieldset").find("input").each(function(){
              var sel = ":nth-child(" + (columnIndex + 1) + ")";
              $(this).jqmData("cells", $("#dtprv").find("tr").children(sel));
              columnIndex++;
              // with another terrible workaround
              if (!this.checked) {
                $(this).click();
                $(this).click();
              }
            });
            $('#dtprv').table('refresh');
          }
        }));
        clearInterval(poll);
      }
    }, 100 );
  }
);
