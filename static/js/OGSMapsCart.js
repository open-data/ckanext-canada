var OGSMapsMaxCart = 2
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
		$(".ogscarttally").text(' Shopping Cart is Empty');
	}
	else if(OGSMapsChecked_ids.length >= OGSMapsMaxCart)
	{
		$(".ogscartlistbtn").show()
		$(".ogscartplotbtn").show()		
		$(".ogscarttally").text(' Shopping Cart is Full');
		cart_full = true
	}
	else
	{
		$(".ogscartlistbtn").show()
		$(".ogscartplotbtn").show()		
		$(".ogscarttally").text(' Shopping Cart ('+OGSMapsChecked_ids.length+' of '+OGSMapsMaxCart+')');
	}

	$(".ogscartbtn").each(function() {
		var action = $(this).attr('id').split('_')
		type = action[0]
		id = action[1]

		cart_has = false
		if(OGSMapsChecked_ids.indexOf(id) > -1) { cart_has = true }

		if(type == 'OGSCartAdd')
		{ 
			if(cart_has) { $(this).hide() }
			else if(cart_full) { $(this).hide() }
			else { $(this).show() }
		}
		else if(type == 'OGSCartRemove')
		{
			if(cart_has) { $(this).show() }
			else { $(this).hide() }
		}
	});


//xx  	<span class="ogscarttally fa-shopping-cart"> Cart 2 of 5</span>
//xx  	<a id="OGSCartListItems" class="ogscartlistbtn btn btn-primary btn-xs"><span class="fa fa-list-alt"></span> List Cart Items [solr query join(cart.items)]</a>
//xx  	<a id="OGSCartPlotItems" class="ogscartplotbtn btn btn-primary btn-xs"><span class="fa fa-globe"></span> Plot Cart Items on a Map [http://path.to.ramp/?arg=join(cart.items)]</a>

//xx  	// Itterate over shopping cart checkboxes to confirm state
//xx  	$('.shoppingCartCheckbox').each(function () {
//xx  		if( jQuery.inArray($(this).val(),OGSMapsChecked_ids) > -1 )
//xx  		{ $(this).attr('checked', true); }
//xx  		else
//xx  		{ $(this).attr('checked', false); }
//xx  	});
//xx  	// Populate the cart management box
//xx  	$('#shoppingCartContent').html(cartStatus(OGSMapsChecked_ids))
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

// Interim function, will change to action on "View On Map"
function alertUpArray()
{
	if(OGSMapsChecked_ids.length === 0)
	{ alert('Select an item to view on RAMP first') }
	else
	{
//		RAMP_ids = []
//		for (var i = OGSMapsChecked_ids.length - 1; i >= 0; i--)
//		{ RAMP_ids.push(OGSMapsChecked_ids[i].split("|")[0]) };
		alert('http://ramp.url/?display='+OGSMapsChecked_ids.join(','))
	}
}
