
(function( $, wb ) {
"use strict";

wb.doc.on('geomap.ready', function(event, maps) {

   var dsMap;

   dsMap = maps.dataset_map;
   if (dsMap) {
    var layer = dsMap.getLayersByName('spatialfeature')[0];
    dsMap.zoomToExtent(layer.getDataExtent().scale(3));
   }

});

})( jQuery, wb );
