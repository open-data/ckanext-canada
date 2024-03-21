this.ckan.module('canada-validation-spec', function($){
  return {
    initialize: function (){
      if( typeof goodtablesUI !== 'undefined' ){
        // modifies the goodtablesUI.spec to add custom descriptions and context
        goodtablesUI.spec['errors']['datastore-invalid-header'] = {
          "name": this._("Invalid Header for DataStore"),
          "message": this._("Column name {value} in column {column_number} is not valid for a DataStore header"),
          "description": this._("Column name is invalid for a DataStore header.\n\n How it could be resolved:\n - Remove any leading underscores('_') from the column name.\n - Remove any leading or trailing white space from the column name.\n - Remove any double quotes('\"') from the column name.\n - Make sure the column name is not blank."),
          "type": "structure",
          "context": "head",
          "weight": 7
        };
        goodtablesUI.spec['errors']['datastore-header-too-long'] = {
          "name": this._("Header Too Long for DataStore"),
          "message": this._("Column name {value} in column {column_number} is too long for a DataStore header"),
          "description": this._("Column name is too long for a DataStore header.\n\n How it could be resolved:\n - Make the column name at most 63 characters long."),
          "type": "structure",
          "context": "head",
          "weight": 7
        };
        goodtablesUI.spec['errors']['invalid-dialect'] = {
          "name": this._("Unsupported Delimiter"),
          "message": this._("File is using delimeter {stream_delimeter} instead of {static_delimeter}"),
          "description": this._("File is using an unsupported delimeter.\n\n How it could be resolved:\n - Use commas (,) as the delimiter."),
          "type": "source-error",
          "context": "table",
          "weight": 7
        };
        goodtablesUI.spec['errors']['invalid-quote-char'] = {
          "name": this._("Unsupported Quote Character"),
          "message": this._("File is using quoting character {stream_quote_char} instead of {static_quote_char}"),
          "description": this._("File is using an unsupported quote character.\n\n How it could be resolved:\n - Use double quotes (\") as the quote character."),
          "type": "source-error",
          "context": "table",
          "weight": 7
        };
        goodtablesUI.spec['errors']['invalid-double-quote'] = {
          "name": this._("Unsupported Double Quoting"),
          "message": this._("File is using double quoting {stream_double_quote} instead of {static_double_quote}"),
          "description": this._("File is not using double quoting.\n\n How it could be resolved:\n - Enable double quoting in the file."),
          "type": "source-error",
          "context": "table",
          "weight": 7
        };
        goodtablesUI.spec['errors']['canada-encoding-error'] = {
          "name": this._("Unsupported File Encdoing"),
          "message": this._("The data source could not be successfully decoded with utf-8 encoding"),
          "description": this._("File is not using utf-8 encoding.\n\n How it could be resolved:\n - Save the file with utf-8 encoding."),
          "type": "source-error",
          "context": "table",
          "weight": 7
        };
      }
    }
  };
});
