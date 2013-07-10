/*!
 * Web Experience Toolkit (WET) / Boîte à outils de l'expérience Web (BOEW)
 * wet-boew.github.com/wet-boew/License-eng.txt / wet-boew.github.com/wet-boew/Licence-fra.txt
 */

/*
 * Les composantes individuelles seront substituées par les compasantes globales
 *
 * Les couche de superpositions seront ajoutés dans l'ordre où ils sont fournis
 * (c'est à dire la première couche sera ajouté en premier, puis la suivante
 * sur le dessus, et ainsi de suite).
 *
 * Prennez note, la carte de base peut être définie globalement dans le fichier settings.js.
 */
var wet_boew_geomap = {
	// OPTIONNEL: Géomap va fournir une carte de base par défaut si aucune carte de base n'est spécifié ici.
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
	},
	*/	
};
