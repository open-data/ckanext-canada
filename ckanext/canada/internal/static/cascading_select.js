window.addEventListener('load', function(){
  $(document).ready(function(){

    let all_options = [];
    let cascading_fields = document.querySelectorAll('[cascading_select_field]');
    let cascading_fields_names = {};
  
    // create child => parent dict
    cascading_fields.forEach(function(element) {
      cascading_fields_names[element.name] = element.getAttribute('cascading_select_field');
    });
  
    // setup the choices for cascading select fields
    cascading_fields.forEach(function(element) {
      let parent = document.getElementsByName(cascading_fields_names[element.name])[0];
      all_options[element.name] = [];
      let x,y;
      for (x=0; x < parent.options.length; x++) {
        if (parent.options[x].value !== "") {
  
          let parent_key = parent.options[x].value;
          all_options[element.name][parent_key] = {};
  
          for(y=0; y < element.options.length; y++) {
            let element_key = element.options[y].value;
            let element_value = element.options[y].innerHTML;
            if (element_key.startsWith(parent_key)) {
              all_options[element.name][parent_key][element_key] = element_value;
            }
          }
        }
      }
      all_options[element.name].length = x;
    });
  
    // register onchange event for cascading select fields
    cascading_fields.forEach(function(element) {
      let parent = document.getElementsByName(cascading_fields_names[element.name])[0];
      parent.onchange = function(){
        let selected_option = parent.options[parent.selectedIndex].value;
  
        // reset cascading select choices
        if (element.name in cascading_fields_names
            && Object.values(cascading_fields_names).includes(element.name)) {
  
          for (let key of Object.keys(cascading_fields_names)) {
            let e = document.getElementsByName(key)[0];
            while (e.options.length) {
              e.remove(0);
            }
          }
        } else {
          while (element.options.length) {
            element.remove(0);
          }
        }
  
        // add new select choices based on selected value of parent field
        let options = all_options[element.name][selected_option];
        element.options.add(new Option("", ""));
        Object.entries(options).forEach(function(opt) {
            element.options.add(new Option(opt[1], opt[0]));
        });
      }
  
    });
  });
});
