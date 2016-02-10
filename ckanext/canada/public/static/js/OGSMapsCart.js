var OGSMapsMaxCart = 5
var OGSMapsChecked_ids = []

// Low cost sanity functions
function uniqueArray(){ OGSMapsChecked_ids = $.grep(OGSMapsChecked_ids, function(v, k){ return $.inArray(v ,OGSMapsChecked_ids) === k; }); }
function cleanCart()
{
	// Duplicates?
	uniqueArray(OGSMapsChecked_ids)

	// Blanks?
	var index = OGSMapsChecked_ids.indexOf('');
	if(index > -1) { OGSMapsChecked_ids.splice(index,1); }

	// Overage?
	// I'm not removing them anymore, this can get sorted now
	//while(OGSMapsChecked_ids.length > OGSMapsMaxCart) { OGSMapsChecked_ids.pop() }
	
	// Adapt for the cookie
	if(OGSMapsChecked_ids.length === 0)
	{ OGSMapsChecked_ids = [] }

	if(OGSMapsChecked_ids.length === 0)
	{ $(".ogscartwrapper").hide() }
	else
	{ $(".ogscartwrapper").show() }
}

function updateCartUI()
{
	cleanCart()

	solr_query = '/maps?q=name%3A%22'+OGSMapsChecked_ids.join("%22+OR+name%3A%22")+'%22+&sort=metadata_modified+desc'
	$('.ogscartlistbtn').attr("href", solr_query)

	cart_full = false
	if(OGSMapsChecked_ids.length === 0)
	{
		$(".ogscartlistbtn").hide()
		$(".ogscartplotbtn").hide()
		// IE 9 adaptation, can't hide them so we disable
		$(".ogscartlistbtn").attr("disabled", "disabled");
		$(".ogscartplotbtn").attr("disabled", "disabled");
		$(".ogscarttally").text(' '+i18n["OGSCart_empty"][wb.lang]);
	}
	else if(OGSMapsChecked_ids.length >= OGSMapsMaxCart)
	{
		$(".ogscartlistbtn").show()
		$(".ogscartplotbtn").show()
		// IE 9 adaptation, can't hide them so we disable
		$(".ogscartlistbtn").removeAttr("disabled");
		$(".ogscartplotbtn").removeAttr("disabled");
		$(".ogscarttally").text(' '+i18n["OGSCart_full"][wb.lang]);
		cart_full = true
	}
	else
	{
		$(".ogscartlistbtn").show()
		$(".ogscartplotbtn").show()
		// IE 9 adaptation, can't hide them so we disable
		$(".ogscartlistbtn").removeAttr("disabled");
		$(".ogscartplotbtn").removeAttr("disabled");
		$(".ogscarttally").text(' '+i18n["OGSCart_has"][wb.lang]+' ('+OGSMapsChecked_ids.length+' '+i18n["OGSCart_of"][wb.lang]+' '+OGSMapsMaxCart+')');
	}

	$(".ogscartbtn").each(function() {
		var action = $(this).attr('id').split('_')
		type = action[0]
		id = action[1]

		cart_has = false
		if(OGSMapsChecked_ids.indexOf(id) > -1) { cart_has = true }

		if(type == 'OGSCartAdd')
		{ 
			if(cart_has)
			{ 
				$(this).hide()
				// IE 9 adaptation, can't hide them so we disable
				$(this).attr("disabled", "disabled");
			}
			else if(cart_full)
			{
				$(this).hide()
				// IE 9 adaptation, can't hide them so we disable
				$(this).attr("disabled", "disabled");
			}
			else
			{
				$(this).show()
				// IE 9 adaptation, can't hide them so we disable
				$(this).removeAttr("disabled");
			}
		}
		else if(type == 'OGSCartRemove')
		{
			if(cart_has)
			{
				$(this).show()
				// IE 9 adaptation, can't hide them so we disable
				$(this).removeAttr("disabled");
			}
			else
			{
				$(this).hide()
				// IE 9 adaptation, can't hide them so we disable
				$(this).attr("disabled", "disabled");
			}
		}
	});
}

// Cart setup
function initCart()
{
	OGSMapsShoppingCart_cookie = readCookie('OGSMapsCookie_cart')
	if (OGSMapsShoppingCart_cookie != null)
	{ OGSMapsChecked_ids = OGSMapsShoppingCart_cookie.split(',') }
	cleanCart()
}

function saveCart()
{
	cleanCart()
    eraseCookie('OGSMapsCookie_cart')
    if(OGSMapsChecked_ids.length > 0)
    { createCookie('OGSMapsCookie_cart',OGSMapsChecked_ids.join(','),30) }
}

function addCartItem(id)
{
    if(OGSMapsChecked_ids.length >= OGSMapsMaxCart)
    {
      alert("The cart can only hold "+OGSMapsMaxCart+" datasets");
      $(this).attr('checked', false);
    }
    else
    { OGSMapsChecked_ids.push(id) }
	saveCart()
}

// This is required for cart management links
function removeCartItem(id)
{
	var index = jQuery.inArray(id,OGSMapsChecked_ids);
	if(index !== -1) { OGSMapsChecked_ids.splice(index, 1) }
	eraseCookie('OGSMapsCookie_cart')
	saveCart()
}

// Part UI ease of use and part system reset
function dumpCart()
{
	OGSMapsChecked_ids = []
	saveCart()
}

// Initiate ramp displaying cart items
function viewOnMap()
{
	if(OGSMapsChecked_ids.length === 0)
	{ alert('Select an item to view on RAMP first') }
	else
	{
		location.href='/ramp/ramp-'+OGSMapsCart_lang+'-ckan.html?keys_disabled='+OGSMapsChecked_ids.join(',')
		//alert('/ramp/ramp-'+OGSMapsCart_lang+'-ckan.html?keys_disabled='+OGSMapsChecked_ids.join(','))
	}
}
