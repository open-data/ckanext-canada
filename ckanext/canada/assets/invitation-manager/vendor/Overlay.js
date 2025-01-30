/*
* Overlay.js
* Contains the fonctions and events for the survey overlay
* tacken from wet github: wb.js, overlay.js, and focus.js
************************ https://github.com/wet-boew/wet-boew/blob/master/src/core/wb.js
************************ https://github.com/wet-boew/wet-boew/blob/master/src/plugins/overlay/overlay.js
************************ https://github.com/wet-boew/wet-boew/blob/master/src/plugins/wb-focus/focus.js
* Customized for not WET theme
*/ 



/***********************************************************************************/
/***********************************************************************************/
/***********************************************************************************/


/*
* wb object: Functions and events for wb object needed for the overlay popup
*/


wb_im = {
	
	initQueue: 0,
	selectors: [],
	doc: $( document ),
	isReady: false,
	isStarted: false,
	seed: 0,
	lang: document.documentElement.lang,
		
		
	/*
	* return boolean of state of disabled flag
	*/
	isDisabled : function() {
		var disabledSaved = "false",
			disabled;
			
		try {
			disabledSaved = localStorage.getItem( "wbdisable" ) || disabledSaved;
		}
		catch ( e ) { }
		
		disabled = currentpage.params.wbdisable || disabledSaved;
		return ( typeof disabled === "string" ) ? ( disabled.toLowerCase() === "true" ) : Boolean ( disabled );
	},
		
		
	/*
	* Remove a selector targeted by timerpoke
	*/
	remove: function( selector ) {
		var len = this.selectors.length,
					i;
		
		for ( i = 0; i != len; i += 1 ) {
			if ( this.selectors[ i ] === selector ) {
				this.selectors.splice( i, 1 );
				break;
			}	
		}
	},
	
	
	/*
	* getId function
	*/
	getId: function() {
			return "wb-auto-" + ( wb.seed += 1 );
	},


	init: function ( event, componentName, selector, noAutoId ) {
		var eventTarget = event.target,
			isEvent = !!eventTarget,
			node = isEvent ? eventTarget : event,
			initedClass = componentName + "-inited",
			isDocumentNode = node === document;
		
		/*
		* Filter out any events triggered by descendents and only initializes
		* the element once (if is an event and document node is not the target)
		*/
		if ( !isEvent || isDocumentNode || ( event.currentTarget === node &&
			node.className.indexOf( initedClass ) === -1 ) ) {
				
			this.initQueue += 1;
			this.remove(selector);
			if ( !isDocumentNode ) {
				node.className += " " + initedClass;
				if ( !noAutoId && !node.id ) {
					node.id = wb.getId();
				}
			}
			return node;
		}
		return document.querySelector(selector);
	},
	
	
	/*
	* ready function
	*/
	ready: function( $elm, componentName, context) {
		if ($elm) {
			// Trigger any nested elements (excluding nested within nested)
			$elm
				.find( wb.allSelectors )
				.addClass( "wb-init" )
				.filter( ":not(#" + $elm.attr( "id" ) + " .wb-init .wb-init)" )
				.trigger( "timerpoke.wb" );
				
			// Identify that the component is ready
			$elm.trigger( "wb-ready." + componentName, context);
			this.initQueue -= 1;
		}
		else {
			this.doc.trigger( "wb-ready." + componentName, context );
		}
		
		// Identify that global initialization is complete
		if ( !this.isReady && this.isStarted && this.initQueue < 1 ) {
			this.isReady = true;
			this.doc.trigger( "wb-ready.wb" );
		}
	},
	
	
	/*
	* start function
	*/
	start: function() {
		// Save a copy of all the possible selectors
		wb.allSelectors = wb.selectors.join( ", ");
		
		// Initiate timerpoke events right way
		wb.timerpoke( true );
		this.isStarted = true;
		this.ready();
		
		// initiate timerpoke events again every half second
		setInterval( wb.timerpoke, 500);
	},
	
	
	/*
	* add function: Add a selector to be targeted by timerpoke
	*/
	add: function( selector ) {
		var exists = false,
			len = wb.selectors.length,
			i;
			
		// Lets ensure we are not running if things are disabled
		if ( wb.isDisabled && selector !== "#wb-tphp" ) {
			return 0;
		}
		
		// Check to see if the selector is already targeted
		for ( i = 0; i !== len; i += 1 ) {
			if (wb.selectors[ i ] === selector ) {
				exists = true; 
				break;
			}
		}
		
		// Add the selector if it isn't already targeted
		if ( !exists ) {
			wb.selectors.push( selector );
		}
	},
	
	
	/* 
	* JQuery escape function -- does not do anything
	*/
	jqEscape : function (str) {return str;} //{ return str.replace(/[#;&,\.\+\*~':"!\^\$\[\]\(\)=>|\/\\]/g, '\\$&'); }
	

};




/********************************************************/
/********************************************************/
/********************************************************/


/*
* overlay functions needed for the survey overlay popup
*/


/* 
* first function to be executed
*/
( function ( $, window, document, wb ) {
	"use strict";
	
	/*
	* Variable and function definitions.
	* These are global to the plugin - meaning that they will be initialized one per page,
	* not once per instance of plugin on the page.
	* So, this is a good place to define variables that are common to all instances
	* of the plugin on the page
	*/
	var componentName = "gc-im-wb-overlay",
		selector = "." + componentName,
		initEvent = "wb-init" + selector,
		closeClass = "overlay-close",
		linkClass = "overlay-lnk",
		ignoreOutsideClass = "outside-off",
		overlayOpenFlag = "gc-im-wb-overlay-dlg",
		initialized = false,
		sourceLinks = {},
		$document = wb.doc,
		i18nText,
		
		
		/*
		* @method init
		* @param (jQuery Event) event Event that triggered the function call
		*/
		init = function ( event) {
			
			/*
			* start initialization
			* returns DOM object = proceed with init
			* return undefined = do not proceed with init (e.g., already initialized)
			*/
			var elm = wb.init( event, componentName, selector ),
				$elm,
				overlayClose;
				
			if ( elm ) {
				$elm = $( elm );
				
				// Only initialize the i18nText once
				if ( !i18nText ) {
					// ii18Text contrains the required language translation for words needed by survey popup (english and french)
					i18nText = {
						close: ( wb.lang === "en" ) ? "Close" : "Fermer", 
						colon: ( wb.lang === "en" ) ? ":" : "&#160;:", 
						space: "&#32;", 
						esc: ( wb.lang === "en" ) ? "(escape key)" : "(touche d\'échappement)", 
						closeOverlay: ( wb.lang === "en" ) ? "Close overlay" : "Fermer la fenêtre superposée" 
					};
				}

				elm.setAttribute( "aria-hidden", "true" );
				
				// Identify that initialization has completed
				initialized = true;
				wb.ready ( $elm, componentName );	

			} 
		},
		
		
		/*
		* openOverlay function
		*/
		openOverlay = function( overlayId, noFocus ) {
			var $overlay = $( "#" + wb.jqEscape( overlayId ) );
			
			$overlay
					.addClass( "open" )
					.attr( "aria-hidden", "false" );
					
			if ( $overlay.hasClass( "wb-popup-full" ) || $overlay.hasClass("wb-popup-mid" ) ) {
				$overlay.attr( "data-pgtitle", document.getElementsByTagName( "H2" )[ 0 ].textContent );
				$document.find( "body" ).addClass( overlayOpenFlag );
			}
			
			if ( !noFocus ) {
				$overlay
						.scrollTop( 0 );
			}
			
			/*
			* Register the overlay if it wasn't previously registered
			* (only required when opening through an event)
			*/
			if ( !sourceLinks[ overlayId ] ) {
				setTimeout( function() {
					sourceLinks[ overlayId ] = null;
				}, 1 );
			}
				
		},
		
		 
		/*
		* closeOverlay function
		*/
		closeOverlay = function( overlayId, noFocus, userClosed ) {
			var $overlay = $( "#" + overlayId ),
				sourceLink = sourceLinks[ overlayId ];
				
			$overlay
					.removeClass( "open" )
					.attr( "aria-hidden", "true" );
					
			if ( $overlay.hasClass( "wb-popup-full" ) || $overlay.hasClass( "wb-popup-mid" ) ) {
				$document.find( "body" ).removeClass( OverlayOpenFlag );
			}
			
			if ( userClosed ) {
				$overlay.addClass( "user-closed" );
			}
			
			// Delete the source link reference
			delete sourceLinks[ overlayId ];
		};
	
	
	
} )( jQuery, window, document, wb_im); 




