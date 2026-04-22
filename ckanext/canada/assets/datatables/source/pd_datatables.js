// NOTE: we use as much functional programming here for Datatables as possible
//       in order to keep things somewhat synchronous and stateless. With re-drawing
//       and re-initializing the table, a full object model can get expensive and
//       unpredictable.
//
//       Using a CKAN module allows us to easily pass variables, use gettext,
//       and initialize on document ready.
this.ckan.module('pd-datatables', function($){
  return {
    /* options object can be extended using data-module-* attributes */
    options : {
      locale: 'en',
      locale_string: 'en-CA',
      timezone_string: 'EST',  // FIXME: EDT / HAE
      csrf_name: null,
      csrf_value: null,
      resource_id: null,
      resource_name: null,
      edit_single_uri: null,
      edit_records_uri: null,
      upsert_records_uri: null,
      delete_records_uri: null,
      ajax_uri: null,
      table_styles: null,
      primary_keys: null,
      foreign_keys: null,
      foreign_links: null,
      chromo_fields: null,
      is_editable: false,
    },
    initialize: function (){
      load_pd_datatable(this);
    }
  };
});

function load_pd_datatable(CKAN_MODULE){
  const _ = CKAN_MODULE._;
  const searchParams = new URLSearchParams(document.location.search);
  const currentDate = new Date().toISOString().split('T')[0];
  const currentYear = new Date().getFullYear();
  const locale = CKAN_MODULE.options.locale;
  const localeString = CKAN_MODULE.options.locale_string;
  const timezoneString = CKAN_MODULE.options.timezone_string;
  const csrfTokenName = CKAN_MODULE.options.csrf_name;
  const csrfTokenValue = CKAN_MODULE.options.csrf_value;
  const resourceID = CKAN_MODULE.options.resource_id;
  const resourceName = CKAN_MODULE.options.resource_name;
  const colOffset = 2;  // expand col + select col
  const defaultRows = 10;
  const ellipsesLength = 100;  // default 100 ellipses length from ckanext-datatablesview
  const editSingleRecordURI = CKAN_MODULE.options.edit_single_uri;
  const editRecordsURI = CKAN_MODULE.options.edit_records_uri;
  const upsertRecordsURI = CKAN_MODULE.options.upsert_records_uri;
  const deleteRecordsURI = CKAN_MODULE.options.delete_records_uri;
  const ajaxURI = CKAN_MODULE.options.ajax_uri;
  const primaryKeys = CKAN_MODULE.options.primary_keys;
  const foreignKeys = CKAN_MODULE.options.foreign_keys;
  const foreignLinks = CKAN_MODULE.options.foreign_links;
  const chromoFields = CKAN_MODULE.options.chromo_fields;
  const isEditable = CKAN_MODULE.options.is_editable;
  const tableStyles = CKAN_MODULE.options.table_styles;
  const EDITOR = pd_datatables__EDITOR;

  const selectAllLabel = _('Select All');
  const colSearchLabel = _('Search:');
  const colSortLabel = _('Sorting by:');
  const colSortAscLabel = _('Ascending');
  const colSortDescLabel = _('Descending');
  const colSortAnyLabel = _('Any');
  const readLessLabel = _('less');
  const rowLabel = _('Row');
  const newBadgeLabel = _('New');
  const updatedBadgeLabel = _('Updated');
  const jumpToPageLabel = _('Jump to page');
  const resetTableLabel = _('Reset Table');
  const fullscreenLabel = _('Fullscreen');
  const exitFullscreenLabel = _('Exit Fullscreen');
  const exitEditTableLabel = _('Exit Edit Mode');
  const fullTableLabel = _('Full Table');
  const compactTableLabel = _('Compact Table');
  const editSingleButtonLabel = _('Edit Online');
  const addInTableButtonLabel = _('Add new record in Table');
  const editInTableButtonLabel = _('Edit<span class="pd-datatbales-btn-count"></span> in Table');
  const validRowLabel = _('Record is valid');
  const errorInRowLabel = _('Some fields have validation errors');
  const requiredInRowLabel = _('Some fields are required');
  const errorSummaryLabel = _('Detailed error summary');
  const fieldErrorSummaryLabel = _('Field errors');
  const leavingEditorWarning = _('You have unsaved records in the table. Do you want to discard your changes or continue editing?');
  const validatingLabel = _('Validating records');
  const savingLabel = _('Saving records to the system');
  const checkMarkSVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 214 214" class="pd-check-circle"><g fill="none" stroke="currentColor" stroke-width="2"><circle class="semi-transparent" fill="currentColor" opacity="0.15" cx="107" cy="107" r="72" ></circle><circle class="colored" fill="currentColor" cx="107" cy="107" r="72" opacity="0.8" ></circle> <polyline stroke="#fff" stroke-width="10" points="73.5,107.8 93.7,127.9 142.2,79.4" style="stroke-dasharray: 50%, 50%; stroke-dashoffset: 100%" /></g></svg>';
  const completeCopy = _('Records saved to the system.');
  const completeSubCopy = _('Would you like to add more records, or preview them in the table?');
  const completeMoreButtonLabel = _('Add more records');
  const completeViewButtonLabel = _('Preview records');
  const validationErrorMessage = _('Your records did not save because one or more of them have errors. Fix the errors and save again to finalize your records.');
  const exceptionErrorMessage = _('Could not save the records due to the following error: ');
  const supprtErrorMessage = _('Your records did not save. Try saving again. If the issue persist please contact support with Support ID: ');
  const genericErrorMessage = _('Your records did not save. Try saving again. If the issue persist please contact support.');
  const dupePrimaryKeysErrorMessage = _('{PRIM_IDS} already used in this Editor Table.');
  const countSuffix = _(' record(s)');
  const editorLegendLabel = _('Legend:');
  const editorLegendValidLabel = _('Valid');
  const editorLegendErrorLabel = _('Error');
  const editorLegendRequiredLabel = _('Required');
  const ajaxErrorMessage = _('Error: Could not query records. Please try again.');
  const excelTemplateErrorMessage = _('Error: Could not generate Excel template. Please try again.');
  const editButtonLabel = _('Edit<span class="pd-datatbales-btn-count"></span> in Excel');
  const exportingButtonLabel = _('Exporting{COUNT} record(s) to an Excel Template');
  const deleteButtonLabel = _('Delete<span class="pd-datatbales-btn-count"></span>');
  const saveButtonLabel = _('Save<span class="pd-datatbales-btn-count"></span>');
  const tableLanguage = {
    decimal: "",
    emptyTable:  '<span id="pd-dtatable-no-records">' + _('No data available in table') + '</span>',
    info: _('Showing _START_ to _END_ of _TOTAL_ entries'),
    infoEmpty: _('Showing 0 to 0 of 0 entries'),
    infoFiltered: _('(filtered from _MAX_ total entries)'),
    infoPostFix: "",
    thousands: ",",
    lengthMenu: _('_MENU_ Show number of entries'),
    loadingRecords: _('Loading...'),
    processing: "",
    search: _('Full Text Search'),
    zeroRecords: '<span id="pd-dtatable-no-records">' + _('No matching records found') + '</span>',
    paginate: {
      first: "«",
      last: "»",
      next: "›",
      previous: "‹"
    },
    aria: {
      orderable: _('Order by this column'),
      orderableReverse: _('Reverse order this column')
    }
  };
  const markedRenderer = new marked.Renderer();
  const numberTypes = [
    'year',
    'month',
    'int',
    'bigint',
    'numeric',
    'float',
    'double',
    'money'
  ];
  const alphaTypes = [
    'text',
    '_text'
  ];
  const supportIDMatch = '<span>Support ID: <em>([0-9]+)</em></span>';

  if( searchParams.has('dt_query') ){
    $([document.documentElement, document.body]).animate({
        scrollTop: $("#dt-preview").offset().top
    }, 0);
  }

  let table;
  let tableState;
  let _savedState = window.localStorage.getItem('DataTables_dtprv_' + window.location.pathname);
  if( _savedState ){
    tableState = JSON.parse(_savedState);
  }
  let isCompactView = typeof tableState != 'undefined' && typeof tableState.compact_view != 'undefined' ? tableState.compact_view : true;
  let isFullScreen = is_page_fullscreen();
  let isEditMode = typeof tableState != 'undefined' && typeof tableState.edit_view != 'undefined' ? tableState.edit_view : false;
  if( isEditMode ){
    $('.pd-datable-instructions').css({'display': 'none'});
  }
  let editingRows = typeof tableState != 'undefined' && typeof tableState.editing_rows != 'undefined' ? tableState.editing_rows : [];
  let isExportingExcel = false;
  let exportingExcelLabel = '<i aria-hidden="true" class="fas fa-spinner"></i>&nbsp;' + exportingButtonLabel.replace('{COUNT}', '');
  let erroredRows = typeof tableState != 'undefined' && typeof tableState.errored_rows != 'undefined' ? tableState.errored_rows : {};
  let requiredRows = typeof tableState != 'undefined' && typeof tableState.required_rows != 'undefined' ? tableState.required_rows : {};
  let filledRows = typeof tableState != 'undefined' && typeof tableState.filled_rows != 'undefined' ? tableState.filled_rows : {};
  let newRecords = [];
  let updatedRecords = [];

  let uri_filters = {};
  if( searchParams.has('dt_query') ){
    let _uri_filters = JSON.parse(searchParams.get('dt_query'));
    for(let [_key, _value] of Object.entries(_uri_filters)){
      let header = $('#dtprv').find('thead').find('th[data-datastore-id="' + _key + '"]');
      if( header.length > 0 ){
        let header_index = $(header).index();
        uri_filters[header_index] = _value
      }
    }
  }

  let availableColumns = [
    {
      "className": "expanders",
      "orderable": false,
      "targets": 0,
      "render": function(_data, _type, _row, _meta){
        if( isEditMode ){
          return _meta.row + 1;
        }
        return _data;
      }
    },
    {"className": "checkboxes", "orderable": false, "targets": 1},
  ];

  DataTable.ext.errMode = function( _settings, _techNote, _message ){
    console.warn(_message);
  };

  DataTable.render.ellipsis = function(_cutoff, _rowIndex, _datatoreID, _isMarkdown){
    return function(_data, _type, _row, _meta){
      if( _type == 'display' ){
        let str = _data.toString();
        let htmlStr = $($.parseHTML(str)).text();
        if( str.length < _cutoff || htmlStr.length < _cutoff ){
          return _isMarkdown ? marked.parse(_data, {renderer: markedRenderer}) : _data;
        }
        let _elementID = 'datatableReadMore_' + _rowIndex + '_' + _datatoreID;
        let expander = '<a class="pd-datatable-readmore-expander" href="javascript:void(0);" data-toggle="collapse" data-bs-toggle="collapse" aria-expanded="false" aria-controls="' +_elementID + '">&#8230;</a>';
        let preview = _isMarkdown ? marked.parse(str.substr(0, _cutoff - 1) + expander + '\n', {renderer: markedRenderer}) : str.substr(0, _cutoff - 1) + expander;
        let remaining = _isMarkdown ? marked.parse(str, {renderer: markedRenderer}) : str.substr(_cutoff - 1);
        return '<div class="pd-datatable-readmore"><span data-markdown="' + _isMarkdown + '">' + preview + '</span><span class="collapse" id="' + _elementID + '">' + remaining + '<a class="pd-datatable-readmore-minimizer" href="javascript:void(0);" data-toggle="collapse" data-bs-toggle="collapse" aria-expanded="true" aria-controls="' + _elementID + '"><small>[' + readLessLabel + ']</small></a><span></div>';
      }
      return _data;
    };
  };

  function bind_readmore(_rowElement){
    let readmores = $('#dtprv').find('.pd-datatable-readmore');
    if( typeof _rowElement != 'undefined' && _rowElement && _rowElement.length > 0 ){
      readmores = $(_rowElement).find('.pd-datatable-readmore');
    }
    if( readmores.length > 0 ){
      $(readmores).each(function(_index, _section){
        if( $(_section).parent('span').children('.pd-datatable-readmore-minimizer').length > 0 ){
          // FIXME: extra [less] is rendering somehow...this is a bad workaround for now...
          $(_section).parent('span').children('.pd-datatable-readmore-minimizer').remove();
        }
        let expandElement = $(_section).find('a.pd-datatable-readmore-expander');
        let minimizeElement = $(_section).find('a.pd-datatable-readmore-minimizer');
        $(_section).find('.collapse').off('hidden.bs.collapse');
        $(_section).find('.collapse').on('hidden.bs.collapse', function(_event){
          $(_section).find('span[data-markdown="true"]').show(0);
          $(expandElement).show(0);
        });
        if( expandElement.length > 0 ){
          $(expandElement).off('click.readMore');
          $(expandElement).on('click.readMore', function(_event){
            _event.stopPropagation();
            $(expandElement).hide(0);
            $(_section).find('.collapse').collapse('show');
            $(_section).find('span[data-markdown="true"]').hide(0);
            if( minimizeElement.length > 0 ){
              $(minimizeElement).focus();
            }
          });
        }
        if( minimizeElement.length > 0 ){
          $(minimizeElement).off('click.readLess');
          $(minimizeElement).on('click.readLess', function(_event){
            _event.stopPropagation();
            $(_section).find('.collapse').collapse('hide');
          });
        }
      });
    }
  }

  function render_highlights(){
    let tableBody = $(table.table().body());
    tableBody.unhighlight();
    if( table.rows({filter: 'applied'}).data().length ){
      table.columns().every(function(_index){
        let column = this;
        if( uri_filters && typeof uri_filters[_index] != 'undefined' ){
          column.search(uri_filters[_index]);
        }
        column.nodes().flatten().to$().unhighlight({className: 'column_highlight'});
        let colSearch = String(column.search());
        let highlightText = colSearch.trim();
        let ds_type = $('.dt-scroll-head').find('th').eq(column.index()).attr('data-datastore-type');
        if( colSearch ){
          if( ds_type == 'numeric' || ds_type == 'float' || ds_type == 'double' || ds_type == 'int' || ds_type == 'bigint' ){
            if( locale == 'en' ){
              highlightText = DataTable.render.number(',', '.', null, null).display(highlightText, null, null);
            }else if( locale == 'fr' ){
              highlightText = DataTable.render.number(' ', ',', null, null).display(highlightText, null, null);
            }else{
              highlightText = DataTable.render.number(null, null, null, null).display(highlightText, null, null);
            }
          }else if( ds_type == 'money' ){
            if( highlightText.toString().includes('$') ){
              highlightText = highlightText.toString().replace('$', '');  // remove dollar signs if present
            }
            if( locale == 'en' ){
              highlightText = DataTable.render.number(',', '.', 2, '$').display(highlightText, null, null);
            }else if( locale == 'fr' ){
              highlightText = DataTable.render.number(' ', ',', 2, null).display(highlightText, null, null) + ' $';
            }else{
              highlightText = DataTable.render.number(null, null, 2, '$').display(highlightText, null, null);
            }
          }
        }
        column.nodes().flatten().to$().highlight(highlightText.split(/\s+/), {className: 'column_highlight'});
      });
      let tableSearch = String(table.search());
      tableBody.highlight(tableSearch.trim().split(/\s+/));
    }
  };

  function render_column_filter(_column, _index){
    let footerContent = $.parseHTML('<span class="dtprv-filter-col"></span>')[0];
    if( _index == 1 ){  // select column
      footerContent = $.parseHTML('<input title="' + selectAllLabel + '" aria-label="' + selectAllLabel + '" id="dt-select-all" name="dt-select-all" type="checkbox"/>')[0];
    }
    if( _index >= colOffset ){
      let headCell = $('#dtprv').find('thead').find('th').eq(_index);
      let ds_type = $(headCell).attr('data-datastore-type');
      let labelText = colSearchLabel + ' ' + $(headCell).attr('data-schema-label');
      let extraClasses = '';
      let colSearch = _column.search();
      let val = String(colSearch).length > 0 ? colSearch : '';
      if( uri_filters && typeof uri_filters[_index] != 'undefined' ){
        val = uri_filters[_index];
      }
      let filterInput = '<input placeholder="' + labelText + '" name="dtprv-filter-col-' + _index + '" id="dtprv-filter-col-' + _index + '" type="text" value="' + val + '" class="form-control form-control-sm" />';
      if( ds_type == 'year' ){
        filterInput = '<input name="dtprv-filter-col-' + _index + '" id="dtprv-filter-col-' + _index + '" data-number-type="int" type="number" min="1899" max="' + currentYear + '" step="1" value="' + val + '" class="form-control form-control-sm" />';
      }else if( ds_type == 'month' ){
        filterInput = '<input name="dtprv-filter-col-' + _index + '" id="dtprv-filter-col-' + _index + '" data-number-type="int" type="number" min="1" max="12" step="1" value="' + val + '" class="form-control form-control-sm" />';
      }else if( ds_type == 'date' ){
        // TODO: add configurable max="' + currentDate + '" ???
        filterInput = '<input name="dtprv-filter-col-' + _index + '" id="dtprv-filter-col-' + _index + '" type="date" min="1899-01-01" value="' + val + '" class="form-control form-control-sm" />';
      }else if( ds_type == 'timestamp' ){
        // TODO: bring back timestamp field when we can do DateTime range filtering in datastore_search!!!
        // TODO: add configurable max="' + currentDate + 'T23:59" ???
        extraClasses = 'dtprv-filter-col-deactive';
        filterInput = '<input tabindex="-1" name="dtprv-filter-col-' + _index + '" id="dtprv-filter-col-' + _index + '" type="datetime-local" min="1899-01-01T00:00" value="' + val + '" class="form-control form-control-sm" />';
      }else if( ds_type == 'int' || ds_type == 'bigint' ){
        filterInput = '<input name="dtprv-filter-col-' + _index + '" id="dtprv-filter-col-' + _index + '" placeholder="' + labelText + '" data-number-type="int" type="text" step="1" value="' + val + '" class="form-control form-control-sm" />';
      }else if( ds_type == 'numeric' || ds_type == 'float' || ds_type == 'double' ){
        filterInput = '<input name="dtprv-filter-col-' + _index + '" id="dtprv-filter-col-' + _index + '" placeholder="' + labelText + '" data-number-type="float" type="text" value="' + val + '" class="form-control form-control-sm" />';
      }else if( ds_type == 'money' ){
        filterInput = '<input name="dtprv-filter-col-' + _index + '" id="dtprv-filter-col-' + _index + '" placeholder="' + labelText + '" data-number-type="money" type="text" value="' + val + '" class="form-control form-control-sm" />';
      }
      footerContent = $.parseHTML('<span class="dtprv-filter-col ' + extraClasses + '"><label for="dtprv-filter-col-' + _index + '" class="sr-only">' + labelText + '</label>' + filterInput + '<button type="submit" class="btn btn-primary btn-small"><i aria-hidden="true" class="fas fa-search"></i><span class="sr-only">' + labelText + '</span></button></span>')[0];
    }
    _column.footer().replaceChildren(footerContent);
    let searchFilterInput = $('#dtprv-filter-col-' + _index);
    if( searchFilterInput.length > 0 ){
      let numberType = $(searchFilterInput).attr('data-number-type');
      $(searchFilterInput).off('keyup.filterCol');
      $(searchFilterInput).on('keyup.filterCol', function(_event){
        let _fVal = $(searchFilterInput).val();
        let commaReplace = locale == 'fr' ? '.' : '';
        if( _event.keyCode == 13 && _column.search() !== _fVal ){
          if( numberType == 'int' && _fVal ){
            _fVal = Math.round(_fVal.replace(' ', '').replace(',', commaReplace));
          }else if( numberType == 'float' && _fVal ){
            _fVal = parseFloat(_fVal.replace(',', commaReplace).replace(' ', ''));
          }else if( numberType == 'money' && _fVal ){
            _fVal = parseFloat(_fVal.replace('$', '').replace(' ', '').replace(',', commaReplace)).toFixed(2);
          }
          $(searchFilterInput).val(_fVal).focus().blur();
          _column.search(_fVal).draw();
        }
      });
    }
  }

  function render_table_footer(){
    let footer = $('#dtprv').find('#dtprv-foot-main');
    if( footer.length > 0 ){
      $('#dtprv').dataTable().api().columns().every(function(_i){
        render_column_filter(this, _i);
      });
      let select_all = $('#dtprv_wrapper').find('.dt-scroll-foot').find('#dt-select-all');
      if( select_all.length > 0 ){
        $(select_all).on("click", function(_event) {
          if( $(select_all).is(":checked") ){
            table.rows().select();
          } else {
            table.rows().deselect();
          }
        });
      }
    }
  }

  function render_cell_input(_value, _rowIndex, _colIndex, _chromo_field){
    let ds_type = _chromo_field.datastore_type;
    let fieldID = 'pd-records_' + _rowIndex + '_' + _chromo_field.datastore_id;
    let editorObject = EDITOR[_chromo_field.datastore_id];
    if( typeof _value == 'undefined' || _value == null ){
      _value = '';
    }
    let readOnly = '';
    let readOnlyClass = '';
    let tabIndex = 0;
    let isPrimaryKey = primaryKeys.includes(_colIndex);
    if( editingRows.length > 0 && primaryKeys.includes(_colIndex) ){
      readOnly = 'readonly';
      readOnlyClass = 'editor-input-readonly';
      tabIndex = -1;
    }
    let maxLength = '';
    if( typeof editorObject.form_attrs != 'undefined' && editorObject.form_attrs && typeof editorObject.form_attrs.maxlength != 'undefined' ){
      maxLength = 'maxlength="' + editorObject.form_attrs.maxlength + '"';
    }
    let srLabel = '<label class="sr-only" for="' + fieldID + '">' + rowLabel + ' ' + (_rowIndex + 1) + ' - ' + editorObject.label + '</label>';
    let fieldInput = '<input class="pd-datatable-editor-input ' + readOnlyClass + '" value="' + _value + '" name=' + fieldID + '" id="' + fieldID + '" data-primary-key="' + isPrimaryKey + '" data-row-index="' + _rowIndex + '" data-datastore-id="' + _chromo_field.datastore_id + '" ' + readOnly + maxLength + ' tabindex="' + tabIndex + '" autocomplete="off" />';
    if( ds_type == 'year' ){
      fieldInput = '<input class="pd-datatable-editor-input ' + readOnlyClass + '" value="' + _value + '" name=' + fieldID + '" id="' + fieldID + '" data-primary-key="' + isPrimaryKey + '" data-row-index="' + _rowIndex + '" data-datastore-id="' + _chromo_field.datastore_id + '" data-number-type="int" type="number" min="1899" max="' + currentYear + '" step="1" ' + readOnly + maxLength + ' tabindex="' + tabIndex + '" autocomplete="off" />';
    }else if( ds_type == 'month' ){
      fieldInput = '<input class="pd-datatable-editor-input ' + readOnlyClass + '" value="' + _value + '" name=' + fieldID + '" id="' + fieldID + '" data-primary-key="' + isPrimaryKey + '" data-row-index="' + _rowIndex + '" data-datastore-id="' + _chromo_field.datastore_id + '" data-number-type="int" type="number" min="1" max="12" step="1" ' + readOnly + maxLength + ' tabindex="' + tabIndex + '" autocomplete="off" />';
    }else if( ds_type == 'date' ){
      // TODO: add configurable max="' + currentDate + '" ???
      fieldInput = '<input class="pd-datatable-editor-input ' + readOnlyClass + '" value="' + _value + '" name=' + fieldID + '" id="' + fieldID + '" data-primary-key="' + isPrimaryKey + '" data-row-index="' + _rowIndex + '" data-datastore-id="' + _chromo_field.datastore_id + '" type="date" min="1899-01-01" ' + readOnly + maxLength + ' tabindex="' + tabIndex + '" autocomplete="off" />';
    }else if( ds_type == 'timestamp' ){
      // TODO: add configurable max="' + currentDate + 'T23:59" ???
      fieldInput = '<input class="pd-datatable-editor-input ' + readOnlyClass + '" value="' + _value + '" name=' + fieldID + '" id="' + fieldID + '" data-primary-key="' + isPrimaryKey + '" data-row-index="' + _rowIndex + '" data-datastore-id="' + _chromo_field.datastore_id + '" type="datetime-local" min="1899-01-01T00:00" ' + readOnly + maxLength + ' tabindex="' + tabIndex + '" autocomplete="off" />';
    }else if( ds_type == 'int' || ds_type == 'bigint' ){
      fieldInput = '<input class="pd-datatable-editor-input ' + readOnlyClass + '" value="' + _value + '" name=' + fieldID + '" id="' + fieldID + '" data-primary-key="' + isPrimaryKey + '" data-row-index="' + _rowIndex + '" data-datastore-id="' + _chromo_field.datastore_id + '" data-number-type="int" type="number" ' + readOnly + maxLength + ' tabindex="' + tabIndex + '" autocomplete="off" />';
    }else if( ds_type == 'numeric' || ds_type == 'float' || ds_type == 'double' ){
      fieldInput = '<input class="pd-datatable-editor-input ' + readOnlyClass + '" value="' + _value + '" name=' + fieldID + '" id="' + fieldID + '" data-primary-key="' + isPrimaryKey + '" data-row-index="' + _rowIndex + '" data-datastore-id="' + _chromo_field.datastore_id + '" data-number-type="float" type="number" ' + readOnly + maxLength + ' tabindex="' + tabIndex + '" autocomplete="off" />';
    }else if( ds_type == 'money' ){
      fieldInput = '<input class="pd-datatable-editor-input ' + readOnlyClass + '" value="' + _value + '" name=' + fieldID + '" id="' + fieldID + '" data-primary-key="' + isPrimaryKey + '" data-row-index="' + _rowIndex + '" data-datastore-id="' + _chromo_field.datastore_id + '" data-number-type="money" type="number" ' + readOnly + maxLength + ' tabindex="' + tabIndex + '" autocomplete="off" />';
    }
    if( typeof editorObject.select_choices != 'undefined' && editorObject.select_choices ){
      let isMultiple = ds_type == '_text' ? 'multiple' : '';
      fieldInput = '<select class="pd-datatable-editor-input ' + readOnlyClass + '" name=' + fieldID + '" id="' + fieldID + '" ' + isMultiple + ' data-primary-key="' + isPrimaryKey + '" data-row-index="' + _rowIndex + '" data-datastore-id="' + _chromo_field.datastore_id + '" ' + readOnly + ' tabindex="' + tabIndex + '" autocomplete="off"><option></option>';
      for( let _i = 0; _i < editorObject.select_choices.length; _i++ ){
        let selected = _value == editorObject.select_choices[_i][0] || (Array.isArray(_value) && _value.includes(editorObject.select_choices[_i][0])) ? 'selected' : '';
        let label = editorObject.select_choices[_i][1];
        if( typeof _chromo_field.datatables_full_text_choices != 'undefined' && _chromo_field.datatables_full_text_choices ){
          label = editorObject.select_choices[_i][0] + _(': ') + label;
        }
        fieldInput += '<option value="' + editorObject.select_choices[_i][0] + '" ' + selected + '>' + label + '</option>';
      }
      fieldInput += '</select>';
    }
    if( (typeof _chromo_field.form_snippet != 'undefined' && _chromo_field.form_snippet.includes('textarea')) || (typeof _chromo_field.markdown != 'undefined' && _chromo_field.markdown) ){
      fieldInput = '<textarea class="pd-datatable-editor-input ' + readOnlyClass + '" name=' + fieldID + '" id="' + fieldID + '" rows="1" data-primary-key="' + isPrimaryKey + '" data-row-index="' + _rowIndex + '" data-datastore-id="' + _chromo_field.datastore_id + '" ' + readOnly + maxLength + ' tabindex="' + tabIndex + '" autocomplete="off">' + _value + '</textarea>';
    }
    // FIXME: form autocomplete needed for Firefox, but is probably really bad for a11y...
    return '<form autocomplete="off">' + srLabel + fieldInput + '<form>';
  }

  function cell_renderer(_data, _type, _row, _meta, _chromo_field){
    if( _type == 'display' ){
      let originalData = _data;
      let showFullTextChoices = false;
      if( typeof _chromo_field.datatables_full_text_choices != 'undefined' && _chromo_field.datatables_full_text_choices ){
        showFullTextChoices = true;
      }
      let colIndex = _meta.col - colOffset;
      if( isEditMode ){
        if( typeof _chromo_field.import_template_include != 'undefined' && ! _chromo_field.import_template_include ){
          return '';  // blank cells for non-editable
        }
        return render_cell_input(_data, _meta.row, colIndex, _chromo_field);
      }
      if( _data == null ){
        return '';  // blank cell for None/null values
      }
      let editorObject = false;
      if( EDITOR ){
        editorObject = EDITOR[_chromo_field.datastore_id];
      }
      if( typeof _chromo_field.markdown != 'undefined' && _chromo_field.markdown ){
        _data = _data.replace('•', '\n-').replace('\r\n•', '\n-').replace('\n•', '\n-').replace('\r•', '\n-').replace(String.fromCharCode(8226), '\n-').replace(String.fromCharCode(183), '\n-');  // replace commonly used list characters
        _data = DataTable.render.ellipsis(ellipsesLength, _meta.row, _chromo_field.datastore_id, true)(_data, _type, _row, _meta);
      }
      if( _chromo_field.datastore_type == '_text' ){
        if( ! Array.isArray(_data) ){
          _data = _data.toString().split(',');  // split to Array if not already
        }
        let displayList = '<ul class="text-left">';
        _data.forEach(function(_val, _i, _arr){
          let _l = _val;
          if( editorObject && showFullTextChoices && typeof editorObject.select_choices != 'undefined' && editorObject.select_choices ){
            for( let _i = 0; _i < editorObject.select_choices.length; _i++ ){
              if( _val == editorObject.select_choices[_i][0] ){
                _l += _(': ') + editorObject.select_choices[_i][1];
                break;
              }
            }
          }
          if( showFullTextChoices ){
            displayList += '<li><span class="pd-datatable-choice-title" title="' + _l + '" aria-label="' + _l + '">' + _val + '</span></li>';
          }else{
            displayList += '<li>' + _val + '</li>';
          }
        });
        displayList += '</ul>';
        _data = displayList;
      }else if( editorObject && showFullTextChoices && typeof editorObject.select_choices != 'undefined' && editorObject.select_choices ){
        for( let _i = 0; _i < editorObject.select_choices.length; _i++ ){
          if( _data == editorObject.select_choices[_i][0] ){
            let _l = originalData + _(': ') + editorObject.select_choices[_i][1];
            _data = '<span class="pd-datatable-choice-title" title="' + _l + '" aria-label="' + _l + '">' + _data + '</span>';
            break;
          }
        }
      }
      if( _data === true ){
        _data = 'TRUE';
      }
      if( _data === false ){
        _data = 'FALSE';
      }
      if( _chromo_field.datastore_type == 'numeric' || _chromo_field.datastore_type == 'int' || _chromo_field.datastore_type == 'bigint' ){
        if( locale == 'en' ){
          _data = DataTable.render.number(',', '.', null, null).display(_data, _type, _row);
        }else if( locale == 'fr' ){
          _data = DataTable.render.number(' ', ',', null, null).display(_data, _type, _row);
        }else{
          _data = DataTable.render.number(null, null, null, null).display(_data, _type, _row);
        }
      }
      if( _chromo_field.datastore_type == 'timestamp' ){
        if( ! _data.toString().includes('+0000') ){
          _data = _data.toString() + '+0000';  // add UTC offset if not present
        }
        _data = new Date(_data).toLocaleString(localeString, {timeZone: "America/Montreal"}) + ' ' + timezoneString;
      }
      if( _chromo_field.datastore_type == 'money' ){
        if( _data.toString().includes('$') ){
          _data = _data.toString().replace('$', '');  // remove dollar signs if present
        }
        if( locale == 'en' ){
          _data = DataTable.render.number(',', '.', 2, '$').display(_data, _type, _row);
        }else if( locale == 'fr' ){
          _data = DataTable.render.number(' ', ',', 2, null).display(_data, _type, _row) + '&nbsp;$';
        }else{
          _data = DataTable.render.number(null, null, 2, '$').display(_data, _type, _row);
        }
      }
      _data = DataTable.render.ellipsis(ellipsesLength, _meta.row, _chromo_field.datastore_id, false)(_data, _type, _row, _meta);
      if( primaryKeys.includes(colIndex) ){
        let pkValue = [];
        for( let _i = 0; _i < primaryKeys.length; _i++ ){
          pkValue.push(String(_row[(primaryKeys[_i] + colOffset)]));
        }
        if( newRecords.length > 0 ){
          for( let _i = 0; _i < newRecords.length; _i++ ){
            if( newRecords[_i].every(function(_val, _idx){ return _val == pkValue[_idx] }) ){
              _data += '<sup><span class="badge pd-datatable-badge pd-datatable-badge-new"><i aria-hidden="true" class="fas fa-star"></i>&nbsp;' + newBadgeLabel + '</span></sup>';
            }
          }
        }
        if( updatedRecords.length > 0 ){
          for( let _i = 0; _i < updatedRecords.length; _i++ ){
            if( updatedRecords[_i].every(function(_val, _idx){ return _val == pkValue[_idx] }) ){
              _data += '<sup><span class="badge pd-datatable-badge pd-datatable-badge-update"><i aria-hidden="true" class="fas fa-star"></i>&nbsp;' + updatedBadgeLabel + '</span></sup>';
            }
          }
        }
      }
      return _data;
    }
    return _data;
  }

  // Compile available columns
  let _sortOrderIndex = 1;
  for( let i = 0; i < chromoFields.length; i++ ){
    if( typeof chromoFields[i].published_resource_computed_field == 'undefined' || ! chromoFields[i].published_resource_computed_field ){
      let previewClass = '';
      if( typeof chromoFields[i].preview_class != 'undefined' ){
        previewClass = chromoFields[i].preview_class;
      }
      if( primaryKeys.includes(i) ){
        previewClass += ' pd-datatables-primary-key-fixed ';
      }
      if( typeof chromoFields[i].import_template_include != 'undefined' && ! chromoFields[i].import_template_include ){
        previewClass += ' pd-datatables-non-editable-col ';
      }
      if( typeof chromoFields[i].datatables_col_class != 'undefined' ){
        previewClass += ' pd-datatables-' + chromoFields[i].datatables_col_class + ' ';
      }
      if( chromoFields[i].datastore_id == 'record_created' || chromoFields[i].datastore_id == 'record_modified' ){
        previewClass += ' pd-datatables-meta-col-lg ';
      }
      availableColumns.push({
        "name": chromoFields[i].datastore_id,
        "className": previewClass,
        "searchable": true,
        "render": function(_data, _type, _row, _meta){
          return cell_renderer(_data, _type, _row, _meta, chromoFields[i]);
        }
      });
      _sortOrderIndex += 1;
    }
  }
  // END
  // Compile available columns
  // END
  const defaultSortOrder = [[_sortOrderIndex - 1, "desc"]];
  sortOrder = defaultSortOrder;

  function is_page_fullscreen(){
    return document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement;
  }

  function open_fullscreen(_element){
    if( _element.requestFullscreen ){
      _element.requestFullscreen();
      isFullScreen = true;
    }else if( _element.webkitRequestFullscreen ){
      _element.webkitRequestFullscreen();
      isFullScreen = true;
    }else if( _element.mozRequestFullScreen ){
      _element.mozRequestFullScreen();
      isFullScreen = true;
    }else if(_element.msRequestFullscreen){
      _element.msRequestFullscreen();
      isFullScreen = true;
    }
  }

  function close_fullscreen(){
    if( document.exitFullscreen ){
      document.exitFullscreen();
      isFullScreen = false;
    }else if( document.webkitExitFullscreen ){
      document.webkitExitFullscreen();
      isFullScreen = false;
    }else if( document.mozExitFullscreen ){
      document.mozExitFullscreen();
      isFullScreen = false;
    }else if( document.msExitFullscreen ){
      document.msExitFullscreen();
      isFullScreen = false;
    }
  }

  function check_the_boxes(_checked, _indexes){
    if( typeof _indexes == 'undefined' ){
      // a cell could be selected with KeyTables
      return;
    }
    let selectCount = table.rows({ selected: true })[0].length;
    let singleSelectButtons = $('#dtprv_wrapper').find('.pd-datatable-btn-single');
    if( selectCount > 1 ){
      $(singleSelectButtons).each(function(_index, _button){
        $(_button).addClass('disabled');
        $(_button).attr('disabled', 'disabled');
      });
    }
    if( isEditable && selectCount > 0 ){
      table.buttons('tableEditorButton:name').text('<i aria-hidden="true" class="fas fa-edit"></i>&nbsp;' + editInTableButtonLabel);
      let buttonStats = $('#dtprv_wrapper').find('span.pd-datatbales-btn-count');
      $(buttonStats).each(function(_index, _button){
        $(_button).html('&nbsp;' + selectCount + countSuffix);
      });
    }else{
      table.buttons('tableEditorButton:name').text('<i aria-hidden="true" class="fas fa-plus"></i>&nbsp;' + addInTableButtonLabel);
      let buttonStats = $('#dtprv_wrapper').find('span.pd-datatbales-btn-count');
      $(buttonStats).each(function(_index, _button){
        $(_button).html('');
      });
    }
    for( let _i = 0; _i < _indexes.length; _i++){
      let checkbox = $($('#dtprv').find('#dtprv-body-main').find('tr:not(.child):not(.validation-error)')[_indexes[_i]]).find('td.checkboxes').find('input[type="checkbox"]');
      $(checkbox)[0].checked = _checked;  // set prop in the scenario that the checkbox has human interaction
      $(checkbox).attr("checked", _checked).blur();
    }
  }

  function render_no_records(){
    let wrapper = $('#dtprv_wrapper').find('.dt-scroll-body');
    if( table.rows()[0].length == 0 ){
      $(wrapper).addClass('pd-datatable-body-main-no-records');
    }else{
      $(wrapper).removeClass('pd-datatable-body-main-no-records');
    }
  }

  function render_human_sorting(){
    let infoWrapper = $('#dtprv_wrapper').find('#dtprv_info');
    if( infoWrapper.length > 0 ){
      $('#dtprv_wrapper').find('.dt-sorting-info').remove();
      let sortInfo = table.order();
      let sortingText = '<span class="info-label">' + colSortLabel + '</span>';
      if( sortInfo.length > 0 ){
        sortingText += '<div>';
        for( let i = 0; i < sortInfo.length; i++ ){
          let column = table.column(sortInfo[i][0]);
          let labelText = column.header().textContent;
          let ds_type = $('#dtprv').find('thead').find('th').eq(column.index()).attr('data-datastore-type');
          sortingText += '<span><em>' + labelText;
          let downIcon = 'fas fa-sort-amount-down';
          let upIcon = 'fas fa-sort-amount-up';
          if( numberTypes.includes(ds_type) ){
            downIcon = 'fas fa-sort-numeric-down-alt';
            upIcon = 'fas fa-sort-numeric-up-alt';
          }else if( alphaTypes.includes(ds_type) ){
            downIcon = 'fas fa-sort-alpha-down-alt';
            upIcon = 'fas fa-sort-alpha-up-alt';
          }
          if( sortInfo[i][1] == 'asc' ){
            sortingText += '<sup><i title="' + colSortAscLabel + '" aria-label="' + colSortAscLabel + '" class="' + upIcon + '"></i></sup>';
          }else if( sortInfo[i][1] == 'desc' ){
            sortingText += '<sup><i title="' + colSortDescLabel + '" aria-label="' + colSortDescLabel + '" class="' + downIcon + '"></i></sup>';
          }else{
            sortingText += '<sup><i title="' + colSortAnyLabel + '" aria-label="' + colSortAnyLabel + '" class="fas fa-random"></i></sup>';
          }
          sortingText += '</em></span>';
        }
        sortingText += '</div>';
      }
      let sortDisplay = '<div class="dt-sorting-info">' + sortingText + '</div>';
      $(infoWrapper).after(sortDisplay);
    }
  }

  function render_pager_input(){
    let pagingWrapper = $('#dtprv_wrapper').find('.dt-paging');
    if( pagingWrapper.length > 0 ){
      $('#dtprv_wrapper').find('.dt-jump-to-page').remove();
      let pageInfo = table.page.info();
      let pageInput = '<div class="dt-jump-to-page"><label for="dt-jump-to-page">' + jumpToPageLabel + '</label><input aria-controls="dtprv" class"form-control form-control-sm" type="number" id="dt-jump-to-page" name="dt-jump-to-page" value="' + (pageInfo.page + 1) + '" min="1" max="' + (pageInfo.pages) + '" /></div>';
      $(pagingWrapper).after(pageInput);
      let jumpToPage = $('#dtprv_wrapper').find('.dt-jump-to-page').find('input');
      if( jumpToPage.length > 0 ){
        $(jumpToPage).off('change.setPage');
        $(jumpToPage).on('change.setPage', function(_event){
          let newPage = parseInt($(jumpToPage).val());
          if( isNaN(newPage) && ! Number.isInteger(newPage) ){
            newPage = 0;
          }else if( newPage >= 1 ){
            newPage -= 1;
          }
          table.page(newPage).draw(false);
        });
      }
    }
  }

  function render_foreign_key_links(){
    $('#dtprv').find('.ref-link').remove();
    if( $.isEmptyObject(foreignKeys) ){
      return;
    }
    let dt_queries = {};
    for(let [_table, _keys] of Object.entries(foreignKeys)){
      dt_queries[_table] = {}
      for(let [_this_key, _that_key] of Object.entries(_keys)){
        let header = $('#dtprv').find('thead').find('th[data-datastore-id="' + _this_key + '"]');
        if( header.length > 0 ){
          let header_index = $(header).index() + 1;
          let data_cells = $('#dtprv').find('#dtprv-body-main').find('td:nth-child(' + header_index + ')');
          if( data_cells.length > 0 ){
            $(data_cells).each(function(_index, _cell){
              $(_cell).attr('data-datastore-id', _this_key);
              let parent_row = $(_cell).parent('tr');
              if( parent_row.length > 0 ){
                let row_index = $(parent_row).index();
                let clone_cell = $(_cell).clone();
                $(clone_cell).find('sup').remove();
                let this_value = $(clone_cell).text();
                if( typeof dt_queries[_table][row_index] == 'undefined' ){
                  dt_queries[_table][row_index] = {
                    'this_keys': [],
                    'dt_query': {}
                  };
                }
                dt_queries[_table][row_index]['this_keys'].push(_this_key);
                dt_queries[_table][row_index]['dt_query'][_that_key] = this_value;
              }
            });
          }
        }
      }
    }
    let table_rows = $('#dtprv').find('#dtprv-body-main').find('tr:not(.child)');
    if( table_rows.length > 0 ){
      $(table_rows).each(function(_index, _row){
        for(let [_table, _rows] of Object.entries(dt_queries)){
          if( typeof _rows[_index] == 'undefined' ){
            continue;
          }
          let ref_uri = foreignLinks[_table];
          let encoded_query = encodeURIComponent(JSON.stringify(_rows[_index]['dt_query']));
          ref_uri += '?dt_query=' +  encoded_query;
          for( _i = 0; _i < _rows[_index]['this_keys'].length; _i++ ){
            let fk_cell = $(_row).find('td[data-datastore-id="' + _rows[_index]['this_keys'][_i] + '"]');
            if( fk_cell.length > 0 ){
              $(fk_cell).append('<sup class="ref-link pd-datatable-ref-link"><small><a target="_blank" href="' + ref_uri + '"><i class="fas fa-external-link-alt"></i></a></small></sup>');
            }
          }
        }
      });
    }
  }

  function render_expand_buttons(){
    let expanderButtons = $('#dtprv').find('td.expanders');
    if( expanderButtons.length > 0){
      $(expanderButtons).each(function(_index, _expanderButton){
        $(_expanderButton).attr('role', 'button');
        $(_expanderButton).attr('aria-controls', 'dtprv-child-data-row-' + _index);
        if( $(_expanderButton).parent().next().hasClass('child') ){
          $(_expanderButton).attr('aria-expanded', true);
        }else{
          $(_expanderButton).attr('aria-expanded', false);
        }
        $(_expanderButton).off('click.Accessible');
        $(_expanderButton).on('click.Accessible', function(_event){
          setTimeout(function(){
            if( $(_expanderButton).parent().next().hasClass('child') ){
              $(_expanderButton).attr('aria-expanded', true);
              bind_readmore($(_expanderButton).parent().next());
            }else{
              $(_expanderButton).attr('aria-expanded', false);
            }
          }, 250);  // there is some transition duration for childRows
        });
      });
      table.off('childRow.Accessible');
      table.on('childRow.Accessible', function(_event, _isShown, _row){
        if( _isShown ){
          let rowIndex = _row.index();
          $(expanderButtons).eq(rowIndex).attr('aria-expanded', true);
          $(expanderButtons).eq(rowIndex).attr('aria-controls', 'dtprv-child-data-row-' + rowIndex);
          $(expanderButtons).eq(rowIndex).parent().next().attr('id', 'dtprv-child-data-row-' + rowIndex);
          bind_readmore($(expanderButtons).eq(rowIndex).parent().next());
        }
      });
    }
  }

  function render_selectbox_inputs(){
    let checkboxes = $('#dtprv').find('td.checkboxes').find('input[type="checkbox"]');
    if( checkboxes.length > 0){
      $(checkboxes).each(function(_index, _checkbox){
        $(_checkbox).off('click.preventSelect');
        $(_checkbox).on('click.preventSelect', function(_event){
          _event.stopPropagation();
        });
        $(_checkbox).off('change.rowSelect');
        $(_checkbox).on('change.rowSelect', function(_event){
          _event.stopPropagation();
          if( $(_checkbox).is(":checked") ){
            table.row(':eq(' + _index + ')').select();
          } else {
            table.row(':eq(' + _index + ')').deselect();
          }
        });
      });
    }
  }

  function _render_failure(_consoleMessage, _message, _type){
    console.warn(_consoleMessage);
    table.processing(false);
    $('#dtprv_processing').css({'display': 'none'});
    $('#dtprv_wrapper').find('#dtprv_failure_message').remove();
    $('#dtprv_wrapper').find('.dt-scroll').before('<div id="dtprv_failure_message" class="alert alert-dismissible show alert-' + _type + '"><p>' + _message + '</p></div>');
  }

  function render_ajax_failure(_message){
    _render_failure(_message, ajaxErrorMessage, 'warning');
  }

  function render_excel_template_failure(_message){
    _render_failure(_message, excelTemplateErrorMessage, 'warning');
  }

  function render_validation_failure(_message){
    _render_failure(_message, validationErrorMessage, 'danger');
  }

  function render_exception_failure(_message, _exceptionMessage){
    _render_failure(_message, exceptionErrorMessage + _exceptionMessage, 'danger');
  }

  function render_generic_failure(_message){
    _render_failure(_message, genericErrorMessage, 'danger');
  }

  function render_support_failure(_message, _supportID){
    _render_failure(_message, supprtErrorMessage + '<pre>' + _supportID + '</pre>', 'danger');
  }

  function set_table_visibility(){
    $('#dtprv').css({'visibility': 'visible'});
    $('table.dataTable').css({'visibility': 'visible'});
    $('.dt-scroll-head').css({'visibility': 'visible'});
    $('.dt-scroll-head').find('th.expanders').css({'visibility': 'visible'});
    $('.dt-length').css({'visibility': 'visible'});
    $('.dt-search').css({'visibility': 'visible'});
    $('#dtprv-editor-button').css({'visibility': 'visible'});
    $('#dtprv-editor-button').find('button').css({'display': 'flex'});
    $('#dtprv_wrapper').attr('data-editable', isEditable);
    $('#dtprv_wrapper').attr('data-compact-view', isCompactView);
    $('#dtprv_wrapper').attr('data-edit-view', isEditMode);
    $('#dtprv_wrapper').find('tr').children('th:first-of-type').css(
      {'width': 'auto', 'min-width': 'auto', 'max-width': 'auto', 'padding': '8px',  'visibility': 'visible'});
    $('#dtprv_wrapper').find('tr').children('td:first-of-type').css(
      {'width': 'auto', 'min-width': 'auto', 'max-width': 'auto', 'padding': '8px',  'visibility': 'visible'});
  }

  function set_state_change_visibility(){
    $('#dtprv').css({'visibility': 'hidden'});
    $('.dt-scroll-head').css({'visibility': 'hidden'});
    $('.dt-scroll-head').find('th.expanders').css({'visibility': 'hidden'});
    $('.dt-length').css({'visibility': 'hidden'});
    $('.dt-search').css({'visibility': 'hidden'});
    $('#dtprv-editor-button').css({'visibility': 'hidden'});
    $('#dtprv-editor-button').find('button').css({'display': 'none'});
  }

  function set_row_selects(){
    if( typeof tableState != 'undefined' && typeof tableState.selected != 'undefined' ){
      table.rows(tableState.selected).select();
      check_the_boxes(true, tableState.selected);
    }
  }

  function set_button_states(){
    if( isEditMode ){
      let hasFilledRows = false;
      let isIncomplete = false;
      let buttonStats = $('#dtprv_wrapper').find('.pd-datatable-save-btn').find('span.pd-datatbales-btn-count');
      for(let [_rowIndex, _erroredCells] of Object.entries(erroredRows)){
        if( _erroredCells.length > 0 ){
          isIncomplete = true;
        }
      }
      for(let [_rowIndex, _requiredCells] of Object.entries(requiredRows)){
        if( _requiredCells.length > 0 ){
          isIncomplete = true;
        }
      }
      let filledCounter = 0;
      for(let [_rowIndex, _filledCells] of Object.entries(filledRows)){
        if( _filledCells.length > 0 ){
          filledCounter += 1;
        }
      }
      if( filledCounter == 0 ){
        hasFilledRows = false;
        $(buttonStats).html('');
      }else{
        hasFilledRows = true;
        $(buttonStats).html('&nbsp;' + filledCounter + countSuffix);
      }
      if( isIncomplete || ! hasFilledRows ){
        table.buttons('saveButton:name').enable(false);
      }else{
        table.buttons('saveButton:name').enable();
      }
    }
    if( isExportingExcel ){
      table.buttons('excelEditorButton:name').enable(false);
    }
    let buttons = $('#dtprv_wrapper').find('.dt-buttons').find('.btn.disabled');
    if( buttons.length > 0 ){
      $(buttons).each(function(_index, _button){
        $(_button).attr('disabled', true);
      });
    }
    if( isEditMode ){
      return;
    }
    let tableModified = false;
    if( ! isCompactView ){
      tableModified = true;
    }
    if( table.search() ){
      tableModified = true;
    }
    if( table.page.len() != defaultRows ){
      tableModified = true;
    }
    let possibleNamedSortIndex = $('#dtprv').find('thead').find('th[data-datastore-id="' + tableState.order[0][0] + '"]').index();
    if( tableState.order.length != defaultSortOrder.length || tableState.order[0][1] != 'desc' || ((tableState.order[0][0] != defaultSortOrder[0][0] && possibleNamedSortIndex != defaultSortOrder[0][0]) || tableState.order[0][1] != defaultSortOrder[0][1]) ){
      tableModified = true;
    }
    if( table.page.info().page > 0 ){
      tableModified = true;
    }
    if( table.rows({selected: true})[0].length > 0 ){
      tableModified = true;
    }
    if( Object.keys(uri_filters).length == 0 ){
      table.columns().every(function(_index){
        if( this.search() ){
          tableModified = true;
        }
      });
    }
    if( tableModified ){
      table.buttons('resetTableButton:name').enable();
    }else{
      table.buttons('resetTableButton:name').enable(false);
    }
  }

  function bind_table_selects(){
    table.off('select.CheckBoxes');
    table.off('deselect.CheckBoxes');
    table.on('select.CheckBoxes', function(e, dt, type, indexes){
      check_the_boxes(true, indexes);
      set_button_states();
      if( table.rows({selected: true})[0].length > 0 ){
        table.buttons('resetTableButton:name').enable();
      }else{
        table.buttons('resetTableButton:name').enable(false);
      }
      if( isExportingExcel ){
        table.buttons('excelEditorButton:name').enable(false);
      }
    }).on('deselect.CheckBoxes', function(e, dt, type, indexes){
      check_the_boxes(false, indexes);
      if( table.rows({selected: true})[0].length > 0 ){
        table.buttons('resetTableButton:name').enable();
      }else{
        table.buttons('resetTableButton:name').enable(false);
      }
      if( isExportingExcel ){
        table.buttons('excelEditorButton:name').enable(false);
      }
    });
  }

  function bind_keyboard_controls(){
    // TODO: allow deep paste into EditMode for CSV/Excel to webform cells???
    let _start = isCompactView ? 0 : 1;
    _start = isEditMode ? 2 : _start;
    $(document).off('keyup.KeyTable');
    $(document).on('keyup.KeyTable', function(_event){
      if( _event.altKey && _event.keyCode == 75 ){  // ALT + k
        _event.stopPropagation();
        table.cell(':eq(' + _start + ')').focus();
        $('.dt-scroll-body')[0].scrollTop = 0;
      }
    });
    table.off('key.KeyTable');
    table.off('key-focus.KeyTable');
    table.off('focus.KeyTable');
    if( isEditMode ){
      // FIXME: key tabling does not work great in Edit Mode, disabled for now...
      table.on('key-focus.KeyTable', function(e, dt, cell, oe){
        $('input', cell.node()).focus();
      });
      table.on('focus.KeyTable', 'td input', function(){
        $(this).select();
      });
    }else{
      table.on('key.KeyTable', function(e, dt, key, cell, oe){
        let rowIndex = cell[0][0].row;
        if( key == 32 ){  // select row on space
          e.preventDefault();
          oe.preventDefault();
          if( table.rows({ selected: true })[0].includes(rowIndex) ){
            table.row(rowIndex).deselect();
          }else{
            table.row(rowIndex).select();
          }
        }
        if( key == 69 ){  // expand on E
          e.preventDefault();
          oe.preventDefault();
          if( isCompactView ){
            let _row = $('#dtprv-body-main').find('tr').eq(rowIndex);
            let _rowObj = table.row(_row);
            if( $(_row).hasClass('dtr-expanded') ){
              _rowObj.child.hide();
              $(_row).removeClass('dtr-expanded');
              $(_row).find('td.expanders').attr('aria-expanded', false);
            }else{
              // workaround the datatable api to use default child renderers
              table.settings()[0].responsive._detailsDisplay(_rowObj, false);
              $(_row).find('td.expanders').attr('aria-expanded', true);
            }
          }
        }
      });
    }
  }

  async function download_excel_template(_uri, _params){
    return new Promise(function(_resolve, _reject){
      let xhr = new XMLHttpRequest();
      xhr.responseType = 'blob';
      xhr.withCredentials = true;
      xhr.onload = function() {
        _resolve(xhr);
      };
      xhr.onerror = _reject;
      xhr.open('POST', _uri);
      xhr.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
      xhr.send(_params);
    }).then(function(_xhr){
      let filename = _uri.substring(_uri.lastIndexOf("/") + 1).split("?")[0];
      let a = document.createElement('a');
      a.href = window.URL.createObjectURL(_xhr.response);
      a.download = filename;
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      a.remove();
      return _xhr;
    });
  }

  function get_available_buttons(){
    let availableButtons = [];

    if ( document.fullscreenEnabled ){
      availableButtons.push({
        name: "fullscreenButton",
        text: (isFullScreen && is_page_fullscreen()) ? '<i aria-hidden="true" class="fas fa-compress"></i>&nbsp;' + exitFullscreenLabel : '<i aria-hidden="true" class="fas fa-expand"></i>&nbsp;' + fullscreenLabel,
        className: 'pd-datatable-btn btn-secondary pd-datatable-fullscreen-btn',
        action: function(e, dt, node, config){
          let datatableSection = $('#dt-preview')[0];
          if( is_page_fullscreen() ){
            close_fullscreen();
            dt.button('fullscreenButton:name').text('<i aria-hidden="true" class="fas fa-expand"></i>&nbsp;' + fullscreenLabel);
            return;
          }else{
            open_fullscreen(datatableSection);
          }
          if( isFullScreen ){
            dt.button('fullscreenButton:name').text('<i aria-hidden="true" class="fas fa-compress"></i>&nbsp;' + exitFullscreenLabel);
          }
        }
      });
      $(document).off('fullscreenchange.setButtonLabel');
      $(document).on('fullscreenchange.setButtonLabel', function(_event){
        if( isFullScreen && is_page_fullscreen() ){
          $('.pd-datatable-fullscreen-btn').html('<i aria-hidden="true" class="fas fa-compress"></i>&nbsp;' + exitFullscreenLabel);
          isFullScreen = true;
        }else{
          $('.pd-datatable-fullscreen-btn').html('<i aria-hidden="true" class="fas fa-expand"></i>&nbsp;' + fullscreenLabel);
          isFullScreen = false;
        }
      });
    }

    if( isEditMode ){
      availableButtons.push({
        name: "saveButton",
        text: '<i aria-hidden="true" class="fas fa-save"></i>&nbsp;' + saveButtonLabel,
        className: 'pd-datatable-btn btn-success pd-datatable-save-btn',
        enabled: false,
        action: function(e, dt, node, config){
          save_table_rows();
        }
      })

      availableButtons.push({
        name: "exitEditButton",
        text: '<i aria-hidden="true" class="fas fa-door-open"></i>&nbsp;' + exitEditTableLabel,
        className: 'pd-datatable-btn btn-warning pd-datatable-exit-edit-btn',
        enabled: true,
        action: function(e, dt, node, config){
          let hasUnsaved = false;
          for(let [_rowIndex, _filledCells] of Object.entries(filledRows)){
            if( _filledCells.length > 0 ){
              hasUnsaved = true;
              break;
            }
          }
          if( hasUnsaved && ! window.confirm(leavingEditorWarning) ){
            return;
          }
          erroredRows = {};
          requiredRows = {};
          filledRows = {};
          set_state_change_visibility();
          table.rows().deselect();
          isCompactView = true;
          isEditMode = false;
          $('.pd-datable-instructions').css({'display': 'block'});
          tableState = void 0;
          dt.state.clear();
          dt.clear().destroy();
          initialize_datatable();
        }
      });
      return availableButtons;
    }

    availableButtons.push({
      name: "tableTypeButton",
      text: isCompactView ? '<i aria-hidden="true" class="fa fa-table"></i>&nbsp;' + fullTableLabel : '<i aria-hidden="true" class="fa fa-list"></i>&nbsp;' + compactTableLabel,
      className: 'pd-datatable-btn btn-info',
      action: function(e, dt, node, config){
        if( isCompactView ){
          dt.button('tableTypeButton:name').text('<i aria-hidden="true" class="fa fa-table"></i>&nbsp;' + compactTableLabel);
          isCompactView = false;
          tableState.compact_view = false;
        }else{
          dt.button('tableTypeButton:name').text('<i aria-hidden="true" class="fa fa-list"></i>&nbsp;' + fullTableLabel);
          isCompactView = true;
          tableState.compact_view = true;
        }
        tableState.selected = table.rows({ selected: true })[0];
        set_state_change_visibility();
        dt.clear().destroy();
        initialize_datatable();
      }
    });

    availableButtons.push({
      name: "resetTableButton",
      text: '<i aria-hidden="true" class="fas fa-sync-alt"></i>&nbsp;' + resetTableLabel,
      className: 'pd-datatable-btn btn-warning pd-datatable-reset-btn',
      enabled: false,
      action: function(e, dt, node, config){
        set_state_change_visibility();
        table.rows().deselect();
        isCompactView = true;
        isEditMode = false;
        $('.pd-datable-instructions').css({'display': 'block'});
        tableState = void 0;
        dt.state.clear();
        dt.clear().destroy();
        initialize_datatable();
      }
    });

    if( EDITOR ){
      availableButtons.push({
        name: "tableEditorButton",
        text: '<i aria-hidden="true" class="fas fa-plus"></i>&nbsp;' + addInTableButtonLabel,
        className: "pd-datatable-btn pd-datatable-editor-btn btn-success",
        action: function(e, dt, button, config){
          editingRows = [];
          if( isEditable ){
            let pk_cols = primaryKeys.map(function(val){
              return val + colOffset;
            });
            let _rows = table.rows({selected: true});
            _rows.eq(0).each(function(index){
              editingRows.push(dt.cells(index, pk_cols).data().toArray());
            });
          }
          set_state_change_visibility();
          table.rows().deselect();
          isCompactView = false;
          isEditMode = true;
          $('.pd-datable-instructions').css({'display': 'none'});
          table.state.save();
          table.clear().destroy();
          initialize_datatable();
        }
      });
    }

    if( isEditable ){
      availableButtons.push({
        extend: "selected",
        name: "excelEditorButton",
        text: isExportingExcel ? exportingExcelLabel : '<i aria-hidden="true" class="fas fa-file-excel"></i>&nbsp;' + editButtonLabel,
        enabled: ! isExportingExcel,
        className: "pd-datatable-btn pd-datatable-excel-btn btn-primary",
        action: function(e, dt, button, config){
          let pk_cols = primaryKeys.map(function(value){
            return value + colOffset;
          });
          let rows = dt.rows({ selected: true });
          let params = new Object();
          params['resource_name'] = resourceName;
          params[csrfTokenName] = csrfTokenValue;
          params['key_indices'] = primaryKeys;
          params['bulk-template'] = [];
          rows.eq(0).each(function(index){
            params['bulk-template'].push(dt.cells(index, pk_cols).data().toArray());
          });
          let urlEncodedData = "";
          let urlEncodedDataPairs = [];
          for( let [_key, _value] of Object.entries(params) ){
            if( Array.isArray(_value) ){
              if( _key == 'bulk-template' ){
                for( let _i = 0; _i < _value.length; _i++ ){
                  urlEncodedDataPairs.push(encodeURIComponent(_key) + '=' + encodeURIComponent(_value[_i].join(',')));
                }
              }else{
                urlEncodedDataPairs.push(encodeURIComponent(_key) + '=' + encodeURIComponent(_value.join(',')));
              }
            }else{
              urlEncodedDataPairs.push(encodeURIComponent(_key) + '=' + encodeURIComponent(_value));
            }
          }
          urlEncodedData = urlEncodedDataPairs.join('&');
          exportingExcelLabel = '<i aria-hidden="true" class="fas fa-spinner"></i>&nbsp;' + exportingButtonLabel.replace('{COUNT}', ' ' + rows[0].length);
          table.buttons('excelEditorButton:name').text(exportingExcelLabel);
          table.buttons('excelEditorButton:name').enable(false);
          isExportingExcel = true;
          download_excel_template(editRecordsURI, urlEncodedData).then(function(){
            table.buttons('excelEditorButton:name').text('<i aria-hidden="true" class="fas fa-file-excel"></i>&nbsp;' + editButtonLabel);
            let buttonStats = $('#dtprv_wrapper').find('.pd-datatable-excel-btn').find('span.pd-datatbales-btn-count');
            let selectCount = table.rows({ selected: true })[0].length;
            if( selectCount > 0 ){
              $(buttonStats).html('&nbsp;' + selectCount + countSuffix);
            }
            table.buttons('excelEditorButton:name').enable();
            isExportingExcel = false;
          }).catch(function(){
            render_excel_template_failure('DataTables error - Failed to generate Excel template');
            isExportingExcel = false;
          });
        }
      });
      availableButtons.push({
        extend: "selected",
        text: '<i aria-hidden="true" class="fas fa-edit"></i>&nbsp;' + editSingleButtonLabel,
        className: "pd-datatable-btn pd-datatable-btn-single btn-success",
        action: function(e, dt, button, config){
          let pk_cols = primaryKeys.map(function(value){
            return value + colOffset;
          });
          let rows = dt.rows({ selected: true });
          if( rows[0].length > 1 ){
            return;
          }
          rows.eq(0).each(function(index){
            let keyString = dt.cells(index, pk_cols).data().toArray();
            let encodedKeyString = encodeURIComponent(keyString.join(','));
            window.location = editSingleRecordURI + encodedKeyString;
          });
        }
      });
    }

    availableButtons.push({
      extend: "selected",
      text: '<i aria-hidden="true" class="fas fa-trash-alt"></i>&nbsp;' + deleteButtonLabel,
      className: "pd-datatable-btn btn-danger",
      action: function(e, dt, button, config){
        // closing form tag needed for py webtest lib
        let form = $('<form></form>', {
          action : deleteRecordsURI,
          method : "post"
        }).append($('<input>').attr({
          type: 'hidden',
          value: resourceName,
          name: 'resource_name'
        })).append($('<input>').attr({
          type: 'hidden',
          value: csrfTokenValue,
          name: csrfTokenName
        })).append($('<input>').attr({
          type: 'hidden',
          value: primaryKeys,
          name: 'key_indices'
        }));
        let pk_cols = primaryKeys.map(function(value){
          return value + colOffset;
        });
        let rows = dt.rows({ selected: true});
        rows.eq(0).each(function(index){
          form.append($('<input>').attr({
            type: 'hidden',
            value: dt.cells(index, pk_cols).data().toArray(),
            name: 'select-delete'
          }));
        });
        form.appendTo('body').submit();
      }
    });

    return availableButtons;
  }

  function save_table_rows(){
    let payload = {
      'resource_id': resourceID,
      'method': editingRows.length > 0 ? 'update' : 'insert',
      'dry_run': true,
      'records': []
    };
    let tokenFieldName = $('meta[name="csrf_field_name"]').attr('content');
    let tokenValue = $('meta[name="' + tokenFieldName + '"]').attr('content');
    payload[tokenFieldName] = tokenValue;
    let tableWrapper = $('#dtprv_wrapper');
    let innerTable = $(tableWrapper).find('#dtprv-body-main');
    for(let [_rowIndex, _filledCells] of Object.entries(filledRows)){
      if( _filledCells.length > 0 ){
        let record = {};
        let row = $(innerTable).find('tr').eq(_rowIndex);
        for( let _i = 0; _i < _filledCells.length; _i++ ){
          record[_filledCells[_i]] = $(row).find('.pd-datatable-editor-input[data-datastore-id="' + _filledCells[_i] + '"]').val();
        }
        payload['records'].push(record);
      }
    }
    payload['records'] = JSON.stringify(payload['records']);
    $(tableWrapper).find('.pd-datatables-editor-loader[data-action="validate"]').css({'display': 'flex'});
    $(tableWrapper).find('.pd-datatables-editor-loader[data-action="validate"]').focus();
    $(tableWrapper).children('.dt-scroll').css({'pointer-events': 'none', 'visibility': 'hidden'});
    $(tableWrapper).children('.dt-buttons').css({'pointer-events': 'none', 'visibility': 'hidden'});
    upsert_data(payload);
  }

  function set_row_errors(_rowIndex, _errObj){
    let row = $('#dtprv_wrapper').find('#dtprv-body-main').find('tr').eq(_rowIndex);
    let colLength = $(row).find('td').length;
    $(row).next('.validation-error').remove();
    if( typeof _errObj.message != 'undefined' && _errObj.message && _errObj.message.length > 0 ){
      $(row).after('<tr class="validation-error"><td class="expanders">' + (parseInt(_rowIndex) + 1) + '</td><td colspan="' + (colLength - 1) + '"><i aria-hidden="true" class="fas fa-exclamation-triangle"></i>&nbsp;' + _errObj.message + '</td></tr>');
    }
    if( typeof _errObj.data != 'undefined' && _errObj.data ){
      for(let [_fieldID, _errArr] of Object.entries(_errObj.data)){
        let _field = $(row).find('.pd-datatable-editor-input[data-datastore-id="' + _fieldID + '"]');
        if( _field.length > 0 ){
          $(_field).parent().find('.validation-error').remove();
          $(_field).parent().append('<div class="validation-error"><i aria-hidden="true" class="fas fa-exclamation-triangle"></i>&nbsp;' + _errArr.join('. ') + '</div>');
          $(_field).css({'box-shadow': '0 0 2px 2px #' + tableStyles.errored.bgColor + ' inset'});
          if( ! erroredRows[_rowIndex].includes(_fieldID) ){
            erroredRows[_rowIndex].push(_fieldID);
          }
        }
      }
    }
    $(row).find('td.expanders').css({'background-color': '#' + tableStyles.errored.bgColor, 'color': '#' + tableStyles.errored.fgColor, 'cursor': 'pointer'})
                               .attr('title', errorInRowLabel)
                               .attr('role', 'button')
                               .attr('tabindex', 0);
  }

  function render_from_editor_response(_data, _payload){
    let tableWrapper = $('#dtprv_wrapper');
    $(tableWrapper).find('#dtprv_failure_message').remove();
    $(tableWrapper).find('.dt-scroll-body')[0].scrollTo(0, 0);
    if( _data.responseJSON ){
      if( _data.responseJSON.success ){
        if( _payload['dry_run'] ){
          $(tableWrapper).find('.pd-datatables-editor-loader[data-action="save"]').css({'display': 'flex'});
          $(tableWrapper).find('.pd-datatables-editor-loader[data-action="save"]').focus();
          $(tableWrapper).children('.dt-scroll').css({'pointer-events': 'none', 'visibility': 'hidden'});
          $(tableWrapper).children('.dt-buttons').css({'pointer-events': 'none', 'visibility': 'hidden'});
          _payload['dry_run'] = false;
          upsert_data(_payload);
        }else{
          if( editingRows.length > 0 ){
            $(tableWrapper).find('#pd-datatables-editor-complete-sub-copy').css({'display': 'none'});
            $(tableWrapper).find('#pd-datatables-editor-complete-more').css({'display': 'none'});
          }else{
            $(tableWrapper).find('#pd-datatables-editor-complete-sub-copy').css({'display': 'inline'});
            $(tableWrapper).find('#pd-datatables-editor-complete-more').css({'display': 'inline-block'});
          }
          $(tableWrapper).find('.pd-datatables-editor-loader[data-action="complete"]').css({'display': 'flex'});
          $(tableWrapper).find('.pd-datatables-editor-loader[data-action="complete"]').focus();
          $(tableWrapper).children('.dt-scroll').css({'pointer-events': 'none', 'visibility': 'hidden'});
          $(tableWrapper).children('.dt-buttons').css({'pointer-events': 'none', 'visibility': 'hidden'});
          if( typeof _data.responseJSON.result != 'undefined' && _data.responseJSON.result ){
            newRecords = [];
            updatedRecords = [];
            let records = _data.responseJSON.result;
            for(let [_index, _record] of Object.entries(records)){
              let pks = [];
              for( let _i = 0; _i < primaryKeys.length; _i++ ){
                pks.push(Object.values(_record.records[0])[primaryKeys[_i]]);
              }
              if( editingRows.length > 0 ){
                updatedRecords.push(pks);
              }else{
                newRecords.push(pks);
              }
            }
          }
          editingRows = [];
          erroredRows = {};
          requiredRows = {};
          filledRows = {};
        }
      }else{
        let errors = _data.responseJSON.error;
        if( typeof errors.message != 'undefined' ){
          render_exception_failure('DataTables error - Could not save data: ' + errors.message, errors.message);
        }else{
          render_validation_failure('DataTables error - Could not save data: one or more records have errors');
          $(tableWrapper).find('.pd-datable-error-summary').remove();
          let errSummary = '<div class="pd-datable-error-summary"><details><summary>' + errorSummaryLabel + '</summary>';
          let filledRowsArray = Object.entries(filledRows);
          for(let [_index, _errObj] of Object.entries(errors)){
            let _rowIndex = parseInt(_index.replace('row_', ''));
            let _fRow = filledRowsArray[_rowIndex];
            if( typeof _fRow != 'undefined' && _fRow.length > 0 ){
              _rowIndex = _fRow[0];
              set_row_errors(_rowIndex, _errObj);
              errSummary += '<div class="pd-datable-error-summary-item"><strong class="pd-datable-error-summary-row-title">' + rowLabel + ' ' + (parseInt(_rowIndex) + 1) + '</strong>';
              if( typeof _errObj.message != 'undefined' && _errObj.message && _errObj.message.length > 0 ){
                errSummary += '<em>' + _errObj.message + '</em><br/>';
              }
              if( typeof _errObj.data != 'undefined' && _errObj.data ){
                errSummary += '<strong>' + fieldErrorSummaryLabel + '</strong><ul>';
                for(let [_fieldID, _errArr] of Object.entries(_errObj.data)){
                  errSummary += '<li><em><a href="javascript:void(0);" class="pd-datable-error-field-link" data-row-index="' + _rowIndex + '" data-field-id="' + _fieldID + '">' + EDITOR[_fieldID].label + '</a></em><ul>';
                  for( let _i = 0; _i < _errArr.length; _i++ ){
                    errSummary += '<li>' + _errArr[_i] + '</li>';
                  }
                  errSummary += '</ul></li>';
                }
                errSummary += '</ul>';
              }
              errSummary += '</div>';
            }else{
              // could not find row in table, probably safe to ignore
              console.warn('DataTables error - Could not locate record in the table...ignoring...');
            }
          }
          errSummary += '</details></div>';
          $(tableWrapper).find('.dt-scroll').before(errSummary);
          let fieldErrorLinks = $(tableWrapper).find('.pd-datable-error-field-link');
          if( fieldErrorLinks.length > 0 ){
            $(fieldErrorLinks).each(function(_index, _fieldErrorLink){
              $(_fieldErrorLink).off('click.GoToError');
              $(_fieldErrorLink).on('click.GoToError', function(_event){
                let rID = $(_fieldErrorLink).attr('data-row-index');
                let fID = $(_fieldErrorLink).attr('data-field-id');
                $(tableWrapper).find('#dtprv-body-main').find('tr').eq(rID).find('td').find('[data-datastore-id="' + fID + '"]').focus();
              });
            });
          }
        }
      }
    }else{
      if( _data.responseText && _data.responseText.length > 0 ){
        let supportID = _data.responseText.match(supportIDMatch);
        if( Array.isArray(supportID) && supportID.length >= 2 ){
          supportID = supportID[1];
          render_support_failure('DataTables error - Could not save data', supportID);
        }else{
          render_generic_failure('DataTables error - Could not save data');
        }
      }else{
        render_generic_failure('DataTables error - Could not save data');
      }
    }
    set_button_states();
  }

  function upsert_data(_payload){
    $.ajax({
      'url': upsertRecordsURI,
      'type': 'POST',
      'dataType': 'JSON',
      'data': _payload,
      'complete': function(_data){
        setTimeout(function(){
          $('#dtprv_wrapper').children('.dt-scroll').css({'pointer-events': 'all', 'visibility': 'visible'});
          $('#dtprv_wrapper').children('.dt-buttons').css({'pointer-events': 'all', 'visibility': 'visible'});
          $('#dtprv_wrapper').find('.pd-datatables-editor-loader').css({'display': 'none'});
          render_from_editor_response(_data, _payload);
        }, 1760);
      }
    });
  }

  function clear_editor(_stayInEditMode){
    editingRows = [];
    erroredRows = {};
    requiredRows = {};
    filledRows = {};
    set_state_change_visibility();
    table.rows().deselect();
    isCompactView = ! _stayInEditMode;
    isEditMode = _stayInEditMode;
    tableState = void 0;
    table.state.clear();
    table.clear().destroy();
    initialize_datatable();
  }

  function set_editor_field_state(_field){
    let tableWrapper = $('#dtprv_wrapper');
    let innerTable = $(tableWrapper).find('#dtprv-body-main');
    let datastoreID = $(_field).attr('data-datastore-id');
    let editorObject = EDITOR[datastoreID];
    let rowIndex = $(_field).attr('data-row-index');
    let row = $(innerTable).find('tr').eq(rowIndex);
    let rowFields = $(row).find('.pd-datatable-editor-input');
    let select2Container = $(_field).prev('.select2-container');
    let fieldValue = $(_field).val();
    $(_field).parent().find('.validation-error').remove();
    if( typeof erroredRows[rowIndex] == 'undefined' ){
      erroredRows[rowIndex] = [];
    }
    if( typeof requiredRows[rowIndex] == 'undefined' ){
      requiredRows[rowIndex] = [];
    }
    if( typeof filledRows[rowIndex] == 'undefined' ){
      filledRows[rowIndex] = [];
    }
    if( typeof fieldValue != 'undefined' && fieldValue.length > 0 && editorObject.is_invalid(fieldValue, rowIndex) ){
      $(_field).css({'box-shadow': '0 0 2px 2px #' + tableStyles.errored.bgColor + ' inset'});
      if( select2Container.length > 0 ){
        $(select2Container).css({'box-shadow': '0 0 2px 2px #' + tableStyles.errored.bgColor + ' inset'});
      }
      if( ! erroredRows[rowIndex].includes(datastoreID) ){
        erroredRows[rowIndex].push(datastoreID);
      }
    }else{
      if( typeof fieldValue == 'undefined' || fieldValue.length == 0 ){
        $(_field).css({'box-shadow': '0 0 1px 1px #d0d0d0 inset'});
        if( select2Container.length > 0 ){
          $(select2Container).css({'box-shadow': '0 0 1px 1px #d0d0d0 inset'});
        }
      }else{
        $(_field).css({'box-shadow': '0 0 2px 2px #' + tableStyles.success.bgColor + ' inset'});
        if( select2Container.length > 0 ){
          $(select2Container).css({'box-shadow': '0 0 2px 2px #' + tableStyles.success.bgColor + ' inset'});
        }
      }
      erroredRows[rowIndex] = erroredRows[rowIndex].filter(function(_arrItem){
        return _arrItem != datastoreID;
      });
    }
    $(rowFields).each(function(_i, _f){
      if( $(_f).hasClass('select2-container') ){
        return;
      }
      let _dsID = $(_f).attr('data-datastore-id');
      let _editorObj = EDITOR[_dsID];
      let _select2Container = $(_f).prev('.select2-container');
      let _cascadingSelectField;
      if( typeof _editorObj.form_attrs != 'undefined' && _editorObj.form_attrs && typeof _editorObj.form_attrs.cascading_select_field != 'undefined' ){
        _cascadingSelectField = _editorObj.form_attrs.cascading_select_field;
      }
      let _v = $(_f).val();
      if( typeof _cascadingSelectField != 'undefined' && _cascadingSelectField == datastoreID ){
        $(_f).find('option').each(function(_i2, _o){
          let _oVal = $(_o).attr('value');
          if( _oVal && _oVal != _v && ! _oVal.startsWith(fieldValue) ){
            $(_o).attr('disabled', true);
          }else{
            $(_o).attr('disabled', null);
          }
        });
        $(_f).select2({
          'datastore-id': _dsID,
          'row-index': rowIndex,
          'allowClear': true,
        });
        _select2Container = $(_f).prev('.select2-container');
      }
      if( typeof _v != 'undefined' && _v.length > 0 && _editorObj.is_invalid(_v, rowIndex) ){
        $(_f).css({'box-shadow': '0 0 2px 2px #' + tableStyles.errored.bgColor + ' inset'});
        if( _select2Container.length > 0 ){
          $(_select2Container).css({'box-shadow': '0 0 2px 2px #' + tableStyles.errored.bgColor + ' inset'}).blur();
        }
        if( ! erroredRows[rowIndex].includes(_dsID) ){
          erroredRows[rowIndex].push(_dsID);
        }
      }else if( _editorObj.is_required(_v, rowIndex) && (typeof _v == 'undefined' || _v.length == 0) ){
        if( ! erroredRows[rowIndex].includes(_dsID) ){
          $(_f).css({'box-shadow': '0 0 2px 2px #' + tableStyles.required.bgColor + ' inset'});
          if( _select2Container.length > 0 ){
            $(_select2Container).css({'box-shadow': '0 0 2px 2px #' + tableStyles.required.bgColor + ' inset'});
          }
        }
        if( ! requiredRows[rowIndex].includes(_dsID) ){
          requiredRows[rowIndex].push(_dsID);
        }
      }else{
        if( typeof _v == 'undefined' || _v.length == 0 ){
          $(_f).css({'box-shadow': '0 0 1px 1px #d0d0d0 inset'});
          if( _select2Container.length > 0 ){
            $(_select2Container).css({'box-shadow': '0 0 1px 1px #d0d0d0 inset'});
          }
        }else{
          $(_f).css({'box-shadow': '0 0 2px 2px #' + tableStyles.success.bgColor + ' inset'});
          if( _select2Container.length > 0 ){
            $(_select2Container).css({'box-shadow': '0 0 2px 2px #' + tableStyles.success.bgColor + ' inset'});
          }
        }
        erroredRows[rowIndex] = erroredRows[rowIndex].filter(function(_arrItem){
          return _arrItem != _dsID;
        });
        requiredRows[rowIndex] = requiredRows[rowIndex].filter(function(_arrItem){
          return _arrItem != _dsID;
        });
      }
      if( typeof _v != 'undefined' && _v.length > 0 ){
        if( ! filledRows[rowIndex].includes(_dsID) ){
          filledRows[rowIndex].push(_dsID);
        }
      }else{
        filledRows[rowIndex] = filledRows[rowIndex].filter(function(_arrItem){
          return _arrItem != _dsID;
        });
      }
    });
    if( filledRows[rowIndex].length == 0 ){
      erroredRows[rowIndex] = [];
      requiredRows[rowIndex] = [];
      $(rowFields).each(function(_i, _f){
        $(_f).css({'box-shadow': '0 0 1px 1px #d0d0d0 inset'});
      });
    }else if( $(_field).attr('data-primary-key') == 'true' ){
      let primaryValues = [];
      // FIXME: why is column offset different if multiple primary keys??
      let primColOffsetEditMode = primaryKeys.length == 1 ? 0 : (colOffset - 1);
      for( let _i = 0; _i < primaryKeys.length; _i++ ){
        primaryValues.push($(rowFields).eq(primaryKeys[_i] + primColOffsetEditMode).val());
      }
      for(let [_rowIndex, _filledCells] of Object.entries(filledRows)){
        if( _rowIndex == rowIndex ){
          continue;
        }
        let _primVals = [];
        let _primIDs = [];
        let _primLabels = [];
        let errMsg = dupePrimaryKeysErrorMessage;
        for( let _i = 0; _i < primaryKeys.length; _i++ ){
          let _f = $(innerTable).find('tr').eq(_rowIndex).find('.pd-datatable-editor-input').eq(primaryKeys[_i] + primColOffsetEditMode);
          if( typeof _f.val() != 'undefined' && _f.val().length > 0 ){
            _primVals.push(_f.val());
            _primIDs.push(_f.attr('data-datastore-id'));
          }
        }
        if( _primVals.length == primaryKeys.length ){
          if( primaryValues.every(function(_v){return _primVals.includes(_v)}) ){
            for( let _i = 0; _i < _primIDs.length; _i++ ){
              let _f = $(row).find('.pd-datatable-editor-input[data-datastore-id="' + _primIDs[_i] + '"]');
              let _select2Container = $(_f).prev('.select2-container');
              $(_f).css({'box-shadow': '0 0 2px 2px #' + tableStyles.errored.bgColor + ' inset'});
              if( _select2Container.length > 0 ){
                $(_select2Container).css({'box-shadow': '0 0 2px 2px #' + tableStyles.errored.bgColor + ' inset'});
              }
              if( ! erroredRows[rowIndex].includes(_primIDs[_i]) ){
                erroredRows[rowIndex].push(_primIDs[_i]);
              }
              let editObj = EDITOR[_primIDs[_i]];
              _primLabels.push(editObj.label);
              set_row_errors(rowIndex, {message: errMsg.replace('{PRIM_IDS}', _primLabels.join(', '))});
            }
          }else{
            for( let _i = 0; _i < _primIDs.length; _i++ ){
              let _f = $(row).find('.pd-datatable-editor-input[data-datastore-id="' + _primIDs[_i] + '"]');
              let _select2Container = $(_f).prev('.select2-container');
              $(_f).css({'box-shadow': '0 0 2px 2px #' + tableStyles.success.bgColor + ' inset'});
              if( _select2Container.length > 0 ){
                $(_select2Container).css({'box-shadow': '0 0 2px 2px #' + tableStyles.success.bgColor + ' inset'});
              }
              erroredRows[rowIndex] = erroredRows[rowIndex].filter(function(_arrItem){
                return _arrItem != _primIDs[_i];
              });
            }
            $(row).next('.validation-error').remove();
          }
        }
      }
    }
    if( erroredRows[rowIndex].length > 0 ){
      $(row).find('td.expanders').css({'background-color': '#' + tableStyles.errored.bgColor, 'color': '#' + tableStyles.errored.fgColor, 'cursor': 'pointer'})
                                 .attr('title', errorInRowLabel)
                                 .attr('role', 'button')
                                 .attr('tabindex', 0);
    }else if( requiredRows[rowIndex].length > 0 ){
      $(row).find('td.expanders').css({'background-color': '#' + tableStyles.required.bgColor, 'color': '#' + tableStyles.required.fgColor, 'cursor': 'pointer'})
                                 .attr('title', requiredInRowLabel)
                                 .attr('role', 'button')
                                 .attr('tabindex', 0);
    }else if( filledRows[rowIndex].length == 0 ){
      $(row).find('td.expanders').css({'background-color': '#555555', 'color': 'white', 'cursor': 'default'})
                                 .attr('title', null)
                                 .attr('role', null)
                                 .attr('tabindex', null);
      $(row).next('.validation-error').remove();
    }else{
      $(row).find('td.expanders').css({'background-color': '#' + tableStyles.success.bgColor, 'color': '#' + tableStyles.success.fgColor, 'cursor': 'default'})
                                 .attr('title', validRowLabel)
                                 .attr('role', null)
                                 .attr('tabindex', null);
    }
    set_button_states();
  }

  function bind_table_editor(){
    $('th[class*="dt-orderable"]').removeClass('dt-orderable').removeClass('dt-orderable-asc').removeClass('dt-ordering-asc').removeClass('dt-orderable-desc').removeClass('dt-ordering-desc');
    set_button_states();
    let tableWrapper = $('#dtprv_wrapper');
    let legendEntryPoint = $(tableWrapper).find('.dt-scroll');
    let innerTable = $(tableWrapper).find('#dtprv-body-main');
    let indexBlocks = $(innerTable).find('td.expanders');
    let fields = $(innerTable).find('.pd-datatable-editor-input');
    if( legendEntryPoint.length > 0 ){
      $(tableWrapper).find('#pd-datatables-editor-legend').remove();
      $(legendEntryPoint).after('<div id="pd-datatables-editor-legend"><strong>' + editorLegendLabel + '</strong>&nbsp;<span class="pd-datatables-legend-success"><em>' + editorLegendValidLabel + '</em></span>&nbsp;&nbsp;<span class="pd-datatables-legend-required"><em>' + editorLegendRequiredLabel + '</em></span>&nbsp;&nbsp;<span class="pd-datatables-legend-error"><em>' + editorLegendErrorLabel + '</em></span></div>')
    }
    if( indexBlocks.length > 0 ){
      $(indexBlocks).each(function(_index, _indexBlock){
        $(_indexBlock).off('click.GoToError');
        $(_indexBlock).off('keyup.GoToError');
        $(_indexBlock).on('click.GoToError', function(_event){
          if( typeof erroredRows[_index] != 'undefined' && erroredRows[_index].length > 0 ){
            $(innerTable).find('tr').eq(_index).find('td').find('[data-datastore-id="' + erroredRows[_index][0] + '"]').focus();
          }else if( typeof requiredRows[_index] != 'undefined' && requiredRows[_index].length > 0 ){
            $(innerTable).find('tr').eq(_index).find('td').find('[data-datastore-id="' + requiredRows[_index][0] + '"]').focus();
          }
        });
        $(_indexBlock).on('keyup.GoToError', function(_event){
          if( _event.keyCode == 13 ){
            if( typeof erroredRows[_index] != 'undefined' && erroredRows[_index].length > 0 ){
              $(innerTable).find('tr').eq(_index).find('td').find('[data-datastore-id="' + erroredRows[_index][0] + '"]').focus();
            }else if( typeof requiredRows[_index] != 'undefined' && requiredRows[_index].length > 0 ){
              $(innerTable).find('tr').eq(_index).find('td').find('[data-datastore-id="' + requiredRows[_index][0] + '"]').focus();
            }
          }
        });
      });
    }
    $(fields).each(function(_index, _field){
      if( $(_field).is('select') ){
        $(_field).select2({
          'datastore-id': $(_field).attr('data-datastore-id'),
          'row-index': $(_field).attr('data-row-index'),
          'allowClear': true,
        });
      }
    });
    $(fields).each(function(_index, _field){
      if( $(_field).hasClass('select2-container') ){
        return;
      }
      if( $(_field).is('textarea') ){
        $(_field).off('keyup.ResizeField');
        $(_field).on('keyup.ResizeField', function(_event){
          $(_field).css({'height': 'auto'});
          $(_field).css({'height': this.scrollHeight + 'px'});
        });
      }
      $(_field).off('change.EDITOR');
      $(_field).on('change.EDITOR', function(_event){
        set_editor_field_state(_field);
      });
      if( editingRows.length > 0 && $(_field).val().length > 0 ){
        $(_field).trigger('change');
      }
    });
  }

  function render_loaders(){
    $('#dtprv_wrapper').prepend('<div data-action="complete" class="pd-datatables-editor-loader"><div>' + checkMarkSVG + '</div><div><p><strong class="text-success">' + completeCopy + '</strong><br/><span id="pd-datatables-editor-complete-sub-copy">' + completeSubCopy + '</span></p></div><div><button id="pd-datatables-editor-complete-more" class="btn btn-success"><i aria-hidden="true" class="fas fa-plus"></i>&nbsp;' + completeMoreButtonLabel + '</button><button id="pd-datatables-editor-complete-preview" class="btn btn-primary"><i aria-hidden="true" class="fas fa-table"></i>&nbsp;' + completeViewButtonLabel + '</button></div></div>');
    $('#dtprv_wrapper').prepend('<div data-action="save" class="pd-datatables-editor-loader"><div><p><strong>' + savingLabel + '</strong></p></div><div id="loader-saving"></div></div>');
    $('#dtprv_wrapper').prepend('<div data-action="validate" class="pd-datatables-editor-loader"><div><p><strong>' + validatingLabel + '</strong></p></div><div id="loader-validating"></div></div>');
    let addMoreButton = $('#dtprv_wrapper').find('#pd-datatables-editor-complete-more');
    let previewButton = $('#dtprv_wrapper').find('#pd-datatables-editor-complete-preview');
    if( addMoreButton.length > 0 ){
      $(addMoreButton).off('click.AddMore');
      $(addMoreButton).on('click.AddMore', function(_event){
        clear_editor(true);
      });
    }
    if( previewButton.length > 0 ){
      $(previewButton).off('click.AddMore');
      $(previewButton).on('click.AddMore', function(_event){
        clear_editor(false);
      });
    }
  }

  function warn_unsaved_records(){
    let hasUnsaved = false;
    for(let [_rowIndex, _filledCells] of Object.entries(filledRows)){
      if( _filledCells.length > 0 ){
        hasUnsaved = true;
        break;
      }
    }
    if( hasUnsaved ){
      return leavingEditorWarning;
    }
  }

  function draw_callback(_settings){
    $('#dtprv_wrapper').find('#dtprv_failure_message').remove();
    set_table_visibility();
    if( ! isEditMode ){
      render_expand_buttons();
      render_selectbox_inputs();
      render_pager_input();
      render_human_sorting();
      render_foreign_key_links();
      set_button_states();
      bind_readmore();
      render_highlights();
      render_no_records();
    }else{
      bind_table_editor();
    }
  }

  function init_callback(){
    set_table_visibility();
    render_loaders();
    if( ! isEditMode ){
      render_table_footer();
      bind_readmore();
      set_row_selects();
      set_button_states();
      if( ! isCompactView ){
        table.columns.adjust();
      }
      bind_table_selects();
      $('.pd-datable-instructions').css({'display': 'block'});
      bind_keyboard_controls();
    }
    if( isEditMode ){
      table.columns.adjust();
      $('.pd-datable-instructions').css({'display': 'none'});
    }
  }

  function initialize_datatable(){
    let keySettings = {
      columns: isCompactView ? ':not(.dtr-hidden)' : ':not(.dtr-hidden):not(.expanders)'
    };
    let selectSettings = {
      style: 'multi',
      selector: 'td:not(:first-child)'
    };
    let searchSettings = {
      return: true
    };
    if( isEditMode ){
      // keyTarget = {columns: ':not(.dtr-hidden):not(.expanders):not(.checkboxes):not(.pd-datatables-non-editable-col)'};
      // FIXME: disabled keyTable in edit more for now...
      keySettings = false;
      selectSettings = false;
      searchSettings = false;
    }
    table = $('#dtprv').DataTable({
      paging: ! isEditMode,
      serverSide: true,
      processing: true,
      responsive: isCompactView,
      autoWidth: true,
      stateSave: true,
      scrollX: ! isCompactView,
      scrollY: 400,
      scrollResize: true,
      scrollCollapse: false,
      deferRender: true,
      keys: keySettings,
      pageLength: isEditMode ? -1 : defaultRows,
      select: selectSettings,
      search: searchSettings,
      searching: ! isEditMode,
      searchHighlight: false,  // we have custom ones that improve it
      order: sortOrder,
      columns: availableColumns,
      dom: "Blfrtip",
      language: tableLanguage,
      ajax: {
        "url": ajaxURI,
        "type": "POST",
        "data": function(_data){
          if( ! isEditMode && Object.keys(uri_filters).length > 0 ){
            for(let [_index, _value] of Object.entries(uri_filters)){
              _data['columns'][_index]['search']['value'] = _value;
            }
          }
          if( isEditMode && editingRows.length > 0 ){
            let pk_cols = primaryKeys.map(function(value){
              return value + colOffset;
            });
            let filteredCols = [];
            for( let _i = 0; _i < editingRows.length; _i++ ){
              for( let _ci = 0; _ci < editingRows[_i].length; _ci++ ){
                if( ! Array.isArray(_data['columns'][pk_cols[_ci]]['search']['value']) ){
                  _data['columns'][pk_cols[_ci]]['search']['value'] = [];
                }
                if( ! _data['columns'][pk_cols[_ci]]['search']['value'].includes(editingRows[_i][_ci]) ){
                  _data['columns'][pk_cols[_ci]]['search']['value'].push(editingRows[_i][_ci]);
                }
                if( ! filteredCols.includes(_ci) ){
                  filteredCols.push(_ci);
                }
              }
            }
            for( let _i = 0; _i < filteredCols.length; _i++ ){
              _data['columns'][pk_cols[_i]]['search']['value'] = JSON.stringify(_data['columns'][pk_cols[_i]]['search']['value']);
            }
          }
          _data['is_edit_mode'] = isEditMode;
        },
        "complete": function(_data){
          if( _data.responseJSON ){
            if( ! _data.responseJSON.aaData ){
              render_ajax_failure('DataTables error - ' + _data.status + ': ' + _data.statusText);
            }
          }else{
            render_ajax_failure('DataTables error - ' + _data.status + ': ' + _data.statusText);
          }
        }
      },
      initComplete: init_callback,
      drawCallback: draw_callback,
      stateSaveParams: function(_settings, _data){
        _data.selected = this.api().rows({selected: true})[0];
        _data.compact_view = isCompactView;
        _data.edit_view = isEditMode;
        _data.editing_rows = editingRows;
        // TODO: save filledRows, erroredRows, requiredRows??? need to save the field values too???
        let localInstanceSelected = typeof tableState != 'undefined' ? tableState.selected : _data.selected;
        tableState = _data;
        tableState.selected = localInstanceSelected;
        tableState.edit_view = isEditMode;
        tableState.editing_rows = editingRows;
      },
      stateLoadParams: function(_settings, _data){
        let localInstanceSelected = typeof tableState != 'undefined' ? tableState.selected : _data.selected;
        tableState = _data;
        tableState.selected = localInstanceSelected;
      },
      buttons: get_available_buttons(),
    });
  }
  window.onbeforeunload = warn_unsaved_records;
  initialize_datatable();
}