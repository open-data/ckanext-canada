window.addEventListener('load', function(){
  $(document).ready(function(){

    let all_options = {};
    let cascading_fields = document.querySelectorAll('[cascading_select_field]');
    let cascading_fields_names = {};

    // create child => parent dict
    cascading_fields.forEach(function(element) {
      cascading_fields_names[element.name] = element.getAttribute('cascading_select_field');
    });

    // Cache original child options grouped by parent values
    cascading_fields.forEach(child => {
      const parent = document.getElementsByName(cascading_fields_names[child.name])[0];
      all_options[child.name] = {};

      for (let i = 0; i < parent.options.length; i++) {
        const parent_val = parent.options[i].value;
        if (parent_val === "") continue;

        all_options[child.name][parent_val] = {};

        for (let j = 0; j < child.options.length; j++) {
          const opt_val = child.options[j].value;
          const opt_text = child.options[j].textContent;

          if (opt_val.startsWith(parent_val)) {
            all_options[child.name][parent_val][opt_val] = opt_text;
          }
        }
      }
    });

    // Recursively clear and update child fields
    function updateChildren(parentName, selectedValue) {
      for (const [childName, thisParent] of Object.entries(cascading_fields_names)) {
        if (thisParent === parentName) {
          const childElement = document.getElementsByName(childName)[0];

          // Clear existing options
          while (childElement.options.length > 0) {
            childElement.remove(0);
          }

          // Add blank option
          childElement.add(new Option("", ""));

          // Add matching options if any
          const options = all_options[childName][selectedValue];
          if (options) {
            for (const [val, label] of Object.entries(options)) {
              childElement.add(new Option(label, val));
            }
          }

          // Recurse further
          updateChildren(childName, childElement.value);

          // Trigger cascading if necessary
          if (childElement.onchange) {
            childElement.onchange();
          }
        }
      }
    }

    // Attach onchange handlers
    cascading_fields.forEach(child => {
      const parent = document.getElementsByName(cascading_fields_names[child.name])[0];

      if (!parent._cascadingAttached) {
        parent._cascadingAttached = true; // Prevent multiple attachments

        parent.addEventListener('change', function () {
          const selected_val = parent.value;
          updateChildren(parent.name, selected_val);
        });
      }
    });

  });
});
