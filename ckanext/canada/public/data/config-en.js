/*!
 * Web Experience Toolkit (WET) / Boîte à outils de l'expérience Web (BOEW)
 * wet-boew.github.com/wet-boew/License-eng.txt / wet-boew.github.com/wet-boew/Licence-fra.txt
 */

/*
 * Global overrides for individual components
 *
 * Map Overlays (i.e. layers)
 * Overlays will be added in the order that they are provided
 * (i.e. the first overlay will be added first, then the next
 * on top, and so on).
 *
 * Note that the basemap can be set globally in settings.js.
 */
var wet_boew_geomap = {
	// OPTIONAL: note that Geomap will provide a default basemap if not specified here.
/*
	basemap : {
		title: 'CBMT',
		type: 'wms',
		url: 'http://geogratis.gc.ca/maps/CBMT',
		layers: 'CBMT',
		format: 'image/png',
		version: '1.1.1',
		options: { singleTile: true, ratio: 1.0, projection: 'EPSG:3978', fractionalZoom: true },
		mapOptions: {
			maxExtent: '-3000000.0, -800000.0, 4000000.0, 3900000.0',			
			maxResolution: 'auto',
			projection: 'EPSG:3978',
			restrictedExtent: '-3000000.0, -800000.0, 4000000.0, 3900000.0',
			units: 'm',
			displayProjection: 'EPSG:4269',
			numZoomLevels: 12
		}
	}
*/
};

