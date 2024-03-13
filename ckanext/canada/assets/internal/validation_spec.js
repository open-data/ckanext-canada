this.ckan.module('canada-validation-spec', function($){
  return {
    initialize: function (){
      if( typeof goodtablesUI !== 'undefined' ){
        // modifies the goodtablesUI.spec to add custom descriptions and context
        goodtablesUI.spec['errors']['datastore-invalid-header'] = {
          "name": this._("Invalid Header for DataStore"),
          "message": this._("Column name {value} in column {column_number} is not valid for a DataStore header"),
          "description": this._("Column name is invalid for a DataStore header.\n\n How it could be resolved:\n - Remove any leading underscores('_') from the column name.\n - Remove any leading or trailing white space from the column name.\n - Remove any double quotes('\"') from the column name.\n - Make sure the column name is not blank."),
          "type": "custom",
          "context": "head",
          "weight": 7
        };
        goodtablesUI.spec['errors']['datastore-header-too-long'] = {
          "name": this._("Header Too Long for DataStore"),
          "message": this._("Column name {value} in column {column_number} is too long for a DataStore header"),
          "description": this._("Column name is too long for a DataStore header.\n\n How it could be resolved:\n - Make the column name at most 63 characters long."),
          "type": "custom",
          "context": "head",
          "weight": 7
        };
        //TODO: improve description for encoding errors and how to fix them.
        //goodtablesUI.spec['errors']['encoding-error'].description = "";
      }
    }
  };
});
