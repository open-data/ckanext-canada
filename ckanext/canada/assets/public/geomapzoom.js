window.addEventListener('load', function(){
    wb.doc.on( "wb-ready.wb-geomap", "#dataset_map", function( event, map ) {
        // Get the map to use in zoomFeature function
        var myMap = map;
        var layer;
        myMap.getLayers().forEach(function (lyr) {
            if (lyr.id == "spatialfeature") {
                layer = lyr;
            }
        });
        extent = layer.getSource().getExtent();
        map.getView().fit(extent, map.getSize());
    });
});
