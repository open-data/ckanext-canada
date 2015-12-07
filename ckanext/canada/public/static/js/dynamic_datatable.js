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
              var $column = $("#dtprv").find("tr").children(sel);
              $(this).jqmData("cells", $column);
              columnIndex++;
              // with an extra workaround
              if (!this.checked) {
                $column.addClass("ui-table-cell-hidden");
              }
            });
          }
        }));
        clearInterval(poll);
      }
    }, 100 );
  }
);
