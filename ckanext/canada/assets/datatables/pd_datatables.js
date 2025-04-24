// NOTE: we use as much functional programming here for Datatables as possible
//       in order to keep things somewhat synchronous and stateless. With re-drawing
//       and re-initializing the table, a full object model can get expensive and
//       unpredictable.

function load_pd_datatable(){
  const searchParams = new URLSearchParams(document.location.search);
  const currentDate = new Date().toISOString().split('T')[0];
  const currentYear = new Date().getFullYear();
  const localeString = pd_datatable__localeString;
  const timezoneString = pd_datatable__timezoneString;
  const csrfTokenValue = pd_datatable__csrfTokenValue;
  const csrfTokenName = pd_datatable__csrfTokenName;
  const resourceName = pd_datatable__resourceName;
  const colOffset = 2;  // expand col + select col
  const defaultRows = 10;
  const ellipsesLength = 100;  // default 100 ellipses length from ckanext-datatablesview
  const primaryKeys = pd_datatable__primaryKeys;
  const foreignKeys = pd_datatable__foreignKeys;
  const foreignLinks = pd_datatable__foreignLinks;
  const chromoFields = pd_datatable__chromoFields;
  const isEditable = pd_datatable__isEditable;
  const selectAllLabel = pd_datatable__selectAllLabel;
  const colSearchLabel = pd_datatable__colSearchLabel;
  const colSortLabel = pd_datatable__colSortLabel;
  const colSortAscLabel = pd_datatable__colSortAscLabel;
  const colSortDescLabel = pd_datatable__colSortDescLabel;
  const colSortAnyLabel = pd_datatable__colSortAnyLabel;
  const readLessLabel = pd_datatable__readLessLabel;
  const jumpToPageLabel = pd_datatable__jumpToPageLabel;
  const resetTableLabel = pd_datatable__resetTableLabel;
  const fullscreenLabel = pd_datatable__fullscreenLabel;
  const exitFullscreenLabel = pd_datatable__exitFullscreenLabel;
  const exitEditTableLabel = pd_datatable__exitEditTableLabel
  const fullTableLabel = pd_datatable__fullTableLabel;
  const compactTableLabel = pd_datatable__compactTableLabel;
  const editSingleButtonLabel = pd_datatable__editSingleButtonLabel;
  const addInTableButtonLabel = pd_datatable__addInTableButtonLabel;
  const editInTableButtonLabel = pd_datatable__editInTableButtonLabel;
  const countSuffix = pd_datatable__countSuffix;
  const ajaxErrorMessage = pd_datatable__ajaxErrorMessage;
  const excelTemplateErrorMessage = pd_datatable__excelTemplateErrorMessage;
  const editSingleRecordURI = pd_datatable__editSingleRecordURI;
  const editButtonLabel = pd_datatable__editButtonLabel;
  const exportingButtonLabel = pd_datatable__exportingButtonLabel;
  const editRecordsURI = pd_datatable__editRecordsURI;
  const deleteButtonLabel = pd_datatable__deleteButtonLabel;
  const deleteRecordsURI = pd_datatable__deleteRecordsURI;
  const saveButtonLabel = pd_datatable__saveButtonLabel;
  const ajaxURI = pd_datatable__ajaxURI;
  const tableLanguage = pd_datatable__tableLanguage;
  const markedRenderer = new marked.Renderer();
  const EDITOR = pd_datatables__EDITOR;

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
  let editingRows = [];
  let isExportingExcel = false;
  let exportingExcelLabel = '<i aria-hidden="true" class="fas fa-spinner"></i>&nbsp;' + exportingButtonLabel.replace('{COUNT}', '');

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
        if( str.length < _cutoff ){
          return _isMarkdown ? marked.parse(_data, {renderer: markedRenderer}) : _data;
        }
        let _elementID = 'datatableReadMore_' + _rowIndex + '_' + _datatoreID;
        let expander = '<a class="pd-datatable-readmore-expander" href="javascript:void(0);" data-toggle="collapse" data-bs-toggle="collapse" aria-expanded="false" aria-controls="' +_elementID + '">&#8230;</a>';
        let preview = _isMarkdown ? marked.parse(str.substr(0, _cutoff-1) + expander + '\n', {renderer: markedRenderer}) : str.substr(0, _cutoff-1) + expander;
        let remaining = _isMarkdown ? marked.parse(str, {renderer: markedRenderer}) : str.substr(_cutoff-1);
        return '<div class="pd-datatable-readmore"><span data-markdown="' + _isMarkdown + '">' + preview + '</span><span class="collapse" id="' + _elementID + '">' + remaining + '<a class="pd-datatable-readmore-minimizer" href="javascript:void(0);" data-toggle="collapse" data-bs-toggle="collapse" aria-expanded="true" aria-controls="' + _elementID + '"><small>[' + readLessLabel + ']</small></a><span></div>';
      }
      return _data;
    };
  };

  function bind_readmore(){
    let readmores = $('#dtprv').find('.pd-datatable-readmore');
    if( readmores.length > 0 ){
      $(readmores).each(function(_index, _section){
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
    // FIXME: highglights for masked data types: money & datetime...
    let tableBody = $(table.table().body());
    tableBody.unhighlight();
    if( table.rows({filter: 'applied'}).data().length ){
      table.columns().every(function(_index){
        let column = this;
        if( uri_filters && typeof uri_filters[_index] != 'undefined' ){
          column.search(uri_filters[_index]);
        }
        column.nodes().flatten().to$().unhighlight({className: 'column_highlight'});
        column.nodes().flatten().to$().highlight(column.search().trim().split(/\s+/), {className: 'column_highlight'});
      });
      tableBody.highlight(table.search().trim().split(/\s+/));
    }
  };

  function render_column_filter(_column, _index){
    let footerContent = $.parseHTML('<span class="dtprv-filter-col"></span>')[0];
    if( _index == 1 ){  // select column
      footerContent = $.parseHTML('<input title="' + selectAllLabel + '" aria-label="' + selectAllLabel + '" id="dt-select-all" name="dt-select-all" type="checkbox"/>')[0];
    }
    if( _index >= colOffset ){
      let ds_type = $('#dtprv').find('thead').find('th').eq(_index).attr('data-datastore-type');
      let labelText = _column.footer().textContent;
      if( ! labelText.includes(colSearchLabel) ){
        labelText = colSearchLabel + ' ' + _column.footer().textContent;
      }
      let val = _column.search().length > 0 ? _column.search() : '';
      if( uri_filters && typeof uri_filters[_index] != 'undefined' ){
        val = uri_filters[_index];
      }
      let filterInput = '<input placeholder="' + labelText + '" name="dtprv-filter-col-' + _index + '" id="dtprv-filter-col-' + _index + '" type="text" value="' + val + '" class="form-control form-control-sm" />';
      if( ds_type == 'year' ){
        filterInput = '<input name="dtprv-filter-col-' + _index + '" id="dtprv-filter-col-' + _index + '" data-number-type="int" type="number" min="1899" max="' + currentYear + '" step="1" value="' + val + '" class="form-control form-control-sm" />';
      }else if( ds_type == 'month' ){
        filterInput = '<input name="dtprv-filter-col-' + _index + '" id="dtprv-filter-col-' + _index + '" data-number-type="int" type="number" min="1" max="12" step="1" value="' + val + '" class="form-control form-control-sm" />';
      }else if( ds_type == 'date' ){
        filterInput = '<input name="dtprv-filter-col-' + _index + '" id="dtprv-filter-col-' + _index + '" type="date" min="1899-01-01" max="' + currentDate + '" value="' + val + '" class="form-control form-control-sm" />';
      }else if( ds_type == 'timestamp' ){
        filterInput = '<input name="dtprv-filter-col-' + _index + '" id="dtprv-filter-col-' + _index + '" type="datetime-local" min="1899-01-01T00:00" max="' + currentDate + 'T23:59" value="' + val + '" class="form-control form-control-sm" />';
      }else if( ds_type == 'int' || ds_type == 'bigint' ){
        filterInput = '<input name="dtprv-filter-col-' + _index + '" id="dtprv-filter-col-' + _index + '" data-number-type="int" type="number" value="' + val + '" step="1" class="form-control form-control-sm" />';
      }else if( ds_type == 'numeric' || ds_type == 'float' || ds_type == 'double' ){
        filterInput = '<input name="dtprv-filter-col-' + _index + '" id="dtprv-filter-col-' + _index + '" data-number-type="float" type="number" value="' + val + '" class="form-control form-control-sm" />';
      }else if( ds_type == 'money' ){
        filterInput = '<input name="dtprv-filter-col-' + _index + '" id="dtprv-filter-col-' + _index + '" data-number-type="money" type="number" value="' + val + '" class="form-control form-control-sm" />';
      }
      // TODO: mask datetimes and money inputs...
      footerContent = $.parseHTML('<span class="dtprv-filter-col"><label for="dtprv-filter-col-' + _index + '" class="sr-only">' + labelText + '</label>' + filterInput + '<button type="submit" class="btn btn-primary btn-small"><i aria-hidden="true" class="fas fa-search"></i><span class="sr-only">' + labelText + '</span></button></span>')[0];
    }
    _column.footer().replaceChildren(footerContent);
    let searchFilterInput = $('#dtprv-filter-col-' + _index);
    if( searchFilterInput.length > 0 ){
      let numberType = $(searchFilterInput).attr('data-number-type');
      $(searchFilterInput).off('keyup.filterCol');
      $(searchFilterInput).on('keyup.filterCol', function(_event){
        if( _event.keyCode == 13 && _column.search() !== $(searchFilterInput).val() ){
          if( numberType == 'int' && $(searchFilterInput).val() ){
            $(searchFilterInput).val(Math.round($(searchFilterInput).val())).focus().blur();
          }
          _column.search($(searchFilterInput).val()).draw();
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

  function render_cell_input(_value, _rowIndex, _chromo_field){
    let ds_type = _chromo_field.datastore_type;
    let fieldID = 'pd-records_' + _rowIndex + '_' + _chromo_field.datastore_id;
    let editorObject = EDITOR[_chromo_field.datastore_id];
    let fieldInput = '<input class="pd-datatable-editor-input" value="' + _value + '" name=' + fieldID + '" id="' + fieldID + '" data-row-index="' + _rowIndex + '" data-datastore-id="' + _chromo_field.datastore_id + '" />';
    if( ds_type == 'year' ){
      fieldInput = '<input class="pd-datatable-editor-input" value="' + _value + '" name=' + fieldID + '" id="' + fieldID + '" data-row-index="' + _rowIndex + '" data-datastore-id="' + _chromo_field.datastore_id + '" data-number-type="int" type="number" min="1899" max="' + currentYear + '" step="1" />';
    }else if( ds_type == 'month' ){
      fieldInput = '<input class="pd-datatable-editor-input" value="' + _value + '" name=' + fieldID + '" id="' + fieldID + '" data-row-index="' + _rowIndex + '" data-datastore-id="' + _chromo_field.datastore_id + '" data-number-type="int" type="number" min="1" max="12" step="1" />';
    }else if( ds_type == 'date' ){
      fieldInput = '<input class="pd-datatable-editor-input" value="' + _value + '" name=' + fieldID + '" id="' + fieldID + '" data-row-index="' + _rowIndex + '" data-datastore-id="' + _chromo_field.datastore_id + '" type="date" min="1899-01-01" max="' + currentDate + '" />';
    }else if( ds_type == 'timestamp' ){
      fieldInput = '<input class="pd-datatable-editor-input" value="' + _value + '" name=' + fieldID + '" id="' + fieldID + '" data-row-index="' + _rowIndex + '" data-datastore-id="' + _chromo_field.datastore_id + '" type="datetime-local" min="1899-01-01T00:00" max="' + currentDate + 'T23:59" />';
    }else if( ds_type == 'int' || ds_type == 'bigint' ){
      fieldInput = '<input class="pd-datatable-editor-input" value="' + _value + '" name=' + fieldID + '" id="' + fieldID + '" data-row-index="' + _rowIndex + '" data-datastore-id="' + _chromo_field.datastore_id + '" data-number-type="int" type="number" />';
    }else if( ds_type == 'numeric' || ds_type == 'float' || ds_type == 'double' ){
      fieldInput = '<input class="pd-datatable-editor-input" value="' + _value + '" name=' + fieldID + '" id="' + fieldID + '" data-row-index="' + _rowIndex + '" data-datastore-id="' + _chromo_field.datastore_id + '" data-number-type="float" type="number" />';
    }else if( ds_type == 'money' ){
      fieldInput = '<input class="pd-datatable-editor-input" value="' + _value + '" name=' + fieldID + '" id="' + fieldID + '" data-row-index="' + _rowIndex + '" data-datastore-id="' + _chromo_field.datastore_id + '" data-number-type="money" type="number" />';
    }
    if( typeof editorObject.select_choices != 'undefined' && editorObject.select_choices ){
      let isMultiple = ds_type == '_text' ? 'multiple' : '';
      fieldInput = '<select class="pd-datatable-editor-input" name=' + fieldID + '" id="' + fieldID + '" ' + isMultiple + ' data-row-index="' + _rowIndex + '" data-datastore-id="' + _chromo_field.datastore_id + '"><option></option>';
      for( let _i = 0; _i < editorObject.select_choices.length; _i++ ){
        // TODO: do checked based on _value and editorObject.select_choices[_i][0]
        fieldInput += '<option value="' + editorObject.select_choices[_i][0] + '">' + editorObject.select_choices[_i][0] + ': ' + editorObject.select_choices[_i][1] + '</option>';
      }
      fieldInput += '</select>';
    }
    if( (typeof _chromo_field.form_snippet != 'undefined' && _chromo_field.form_snippet.includes('textarea')) || (typeof _chromo_field.markdown != 'undefined' && _chromo_field.markdown) ){
      fieldInput = '<textarea class="pd-datatable-editor-input" name=' + fieldID + '" id="' + fieldID + '" rows="1" data-row-index="' + _rowIndex + '" data-datastore-id="' + _chromo_field.datastore_id + '">' + _value + '</textarea>';
    }
    // TODO: mask datetimes and money inputs...
    return fieldInput;
  }

  function cell_renderer(_data, _type, _row, _meta, _chromo_field){
    // FIXME: any data transormations for masks in _type == 'search'
    if( _type == 'display' ){
      if( isEditMode ){
        if( typeof _chromo_field.import_template_include != 'undefined' && ! _chromo_field.import_template_include ){
          return '';  // blank cells for non-editable
        }
        return render_cell_input(_data, _meta.row, _chromo_field);
      }
      if( _data == null ){
        return '';  // blank cell for None/null values
      }
      if( typeof _chromo_field.markdown != 'undefined' && _chromo_field.markdown ){
        _data = _data.replace('•', '\n-').replace('\r\n•', '\n-').replace('\n•', '\n-').replace('\r•', '\n-').replace(String.fromCharCode(8226), '\n-').replace(String.fromCharCode(183), '\n-');  // replace commonly used list characters
        return DataTable.render.ellipsis(ellipsesLength, _meta.row, _chromo_field.datastore_id, true)(_data, _type, _row, _meta);
      }
      if( _chromo_field.datastore_type == '_text' ){
        if( ! Array.isArray(_data) ){
          _data = _data.toString().split(',');  // split to Array if not already
        }
        let displayList = '<ul style="text-align:left;">';
        _data.forEach(function(_val, _i, _arr){
          displayList += '<li>' + _val + '</li>';
        });
        displayList += '</ul>';
        return displayList;
      }
      if( _data === true ){
        return 'TRUE';
      }
      if( _data === false ){
        return 'FALSE';
      }
      if( _chromo_field.datastore_type == 'numeric' || _chromo_field.datastore_type == 'int' || _chromo_field.datastore_type == 'bigint' ){
        return DataTable.render.number().display(_data, _type, _row);
      }
      if( _chromo_field.datastore_type == 'timestamp' ){
        if( ! _data.toString().includes('+0000') ){
          _data = _data.toString() + '+0000';  // add UTC offset if not present
        }
        return new Date(_data).toLocaleString(localeString, {timeZone: "America/Montreal"}) + ' ' + timezoneString;
      }
      if( _chromo_field.datastore_type == 'money' ){
        if( _data.toString().includes('$') ){
          _data = _data.toString().replace('$', '');  // remove dollar signs if present
        }
        return DataTable.render.number(null, null, 2, '$').display(_data, _type, _row);
      }
      return DataTable.render.ellipsis(ellipsesLength, _meta.row, _chromo_field.datastore_id, false)(_data, _type, _row, _meta);
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
    if( selectCount > 0 ){
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
      let checkbox = $($('#dtprv').find('#dtprv-body-main').find('tr')[_indexes[_i]]).find('td.checkboxes').find('input[type="checkbox"]');
      $(checkbox)[0].checked = _checked;  // set prop in the scenario that the checkbox has human interaction
      $(checkbox).attr("checked", _checked).blur();
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
          // TODO: do numeric and alphabetic sorting based on ds_type...
          if( sortInfo[i][1] == 'asc' ){
            sortingText += '<sup><i title="' + colSortAscLabel + '" aria-label="' + colSortAscLabel + '" class="fas fa-sort-amount-up"></i></sup>';
          }else if( sortInfo[i][1] == 'desc' ){
            sortingText += '<sup><i title="' + colSortDescLabel + '" aria-label="' + colSortDescLabel + '" class="fas fa-sort-amount-down"></i></sup>';
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
                let this_value = $(_cell).text();
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
    let table_rows = $('#dtprv').find('#dtprv-body-main').find('tr');
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
              $(fk_cell).append('<sup class="ref-link" style="opacity:0.65;margin-left:4px"><small style="font-size:75%;"><a target="_blank" href="' + ref_uri + '"><i class="fas fa-external-link-alt"></i></a></small></sup>');
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

  function render_ajax_failure(_message){
    console.warn(_message);
    table.processing(false);
    $('#dtprv_processing').css({'display': 'none'});
    $('#dtprv_wrapper').find('#dtprv_failure_message').remove();
    $('#dtprv_wrapper').find('.dt-scroll').before('<div id="dtprv_failure_message" class="alert alert-dismissible show alert-warning"><p>' + ajaxErrorMessage + '</p></div>');
  }

  function render_excel_template_failure(_message){
    console.warn(_message);
    table.processing(false);
    $('#dtprv_processing').css({'display': 'none'});
    $('#dtprv_wrapper').find('#dtprv_failure_message').remove();
    $('#dtprv_wrapper').find('.dt-scroll').before('<div id="dtprv_failure_message" class="alert alert-dismissible show alert-warning"><p>' + excelTemplateErrorMessage + '</p></div>');
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
    if( isExportingExcel ){
      table.buttons('excelEditorButton:name').enable(false);
    }
    let buttons = $('#dtprv_wrapper').find('.dt-buttons').find('.btn.disabled');
    if( buttons.length > 0 ){
      $(buttons).each(function(_index, _button){
        $(_button).attr('disabled', true);
      });
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
    // TODO: allow deep paste into EditMode for CSV/Excel to webform cells!!!
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
      // FIXME: focus into inputs and allow for keying inside inputs!!!
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

  function download_excel_template(_uri, _params){
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
        // TODO: update button label with number added + countSuffix
        text: '<i aria-hidden="true" class="fas fa-save"></i>&nbsp;' + saveButtonLabel,
        className: 'pd-datatable-btn btn-success pd-datatable-save-btn',
        enabled: false,
        action: function(e, dt, node, config){
          // TODO: write ajax POST to datastore_upsert API.
          //       action=insert for create, action=update for edit
        }
      })

      availableButtons.push({
        name: "exitEditButton",
        text: '<i aria-hidden="true" class="fas fa-door-open"></i>&nbsp;' + exitEditTableLabel,
        className: 'pd-datatable-btn btn-warning pd-datatable-exit-edit-btn',
        enabled: true,
        action: function(e, dt, node, config){
          // TODO: check if there are new/changes fields and then alert of unsaved work...
          set_state_change_visibility();
          table.rows().deselect();
          isCompactView = true;
          isEditMode = false;
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
        tableState = void 0;
        dt.state.clear();
        dt.clear().destroy();
        initialize_datatable();
      }
    });

    if( isEditable && EDITOR ){
      availableButtons.push({
        name: "tableEditorButton",
        text: '<i aria-hidden="true" class="fas fa-plus"></i>&nbsp;' + addInTableButtonLabel,
        className: "pd-datatable-btn pd-datatable-editor-btn btn-success",
        action: function(e, dt, button, config){
          editingRows = table.rows({selected: true})[0];
          set_state_change_visibility();
          table.rows().deselect();
          isCompactView = false;
          isEditMode = true;
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
          // FIXME: bulk-template and key_indices multiple!!!
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
              urlEncodedDataPairs.push(encodeURIComponent(_key) + '=' + encodeURIComponent(_value.join(',')));
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

  function bind_table_editor(){
    $('th[class*="dt-orderable"]').removeClass('dt-orderable').removeClass('dt-orderable-asc').removeClass('dt-ordering-asc').removeClass('dt-orderable-desc').removeClass('dt-ordering-desc');
    let tableWrapper = $('#dtprv_wrapper');
    let innerTable = $(tableWrapper).find('#dtprv-body-main');
    let fields = $(innerTable).find('.pd-datatable-editor-input');
    if( editingRows.length == 0 ){

    }
    // TODO: on browser nav alert unsaved!!!
    let erroredRows = {};
    let requiredRows = {};
    $(fields).each(function(_index, _field){
      $(_field).off('change.EDITOR');
      $(_field).on('change.EDITOR', function(_event){
        let datastoreID = $(_field).attr('data-datastore-id')
        let editorObject = EDITOR[datastoreID];
        let rowIndex = $(_field).attr('data-row-index');
        let row = $(innerTable).find('tr').eq(rowIndex);
        let rowFields = $(row).find('.pd-datatable-editor-input');
        // TODO: click to go to error...
        // TODO: check required fields!!!
        if( typeof erroredRows[rowIndex] == 'undefined' ){
          erroredRows[rowIndex] = [];
        }
        if( editorObject.is_invalid($(_field).val()) ){
          $(_field).css({'box-shadow': '0 0 2px 2px #C00000 inset'});
          if( ! erroredRows[rowIndex].includes(datastoreID) ){
            erroredRows[rowIndex].push(datastoreID);
          }
        }else{
          $(_field).css({'box-shadow': '0 0 2px 2px #1e7e34 inset'});
          erroredRows[rowIndex] = erroredRows[rowIndex].filter(function(_arrItem){
            return _arrItem != datastoreID;
          });
        }
        if( erroredRows[rowIndex].length > 0 ){
          $(row).find('td.expanders').css({'background-color': '#C00000'});
        }else{
          $(row).find('td.expanders').css({'background-color': '#1e7e34'});
        }
      });
    });
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
      if( uri_filters ){
        render_highlights();
      }
    }else{
      bind_table_editor();
    }
  }

  function init_callback(){
    set_table_visibility();
    if( ! isEditMode ){
      render_table_footer();
      bind_readmore();
      set_row_selects();
      set_button_states();
      if( ! isCompactView ){
        table.columns.adjust();
      }
      bind_table_selects();
    }
    bind_keyboard_controls();
    if( isEditMode ){
      // FIXME: non-editable cols widths when changing states and reinitializing...
      table.columns.adjust();
    }
  }

  function initialize_datatable(){
    let keyTarget = isCompactView ? ':not(.dtr-hidden)' : ':not(.dtr-hidden):not(.expanders)';
    let selectSettings = {
      style: 'multi',
      selector: 'td:not(:first-child)'
    }
    if( isEditMode ){
      keyTarget = ':not(.dtr-hidden):not(.expanders):not(.checkboxes):not(.pd-datatables-non-editable-col)';
      selectSettings = false;
    }
    table = $('#dtprv').DataTable({
      paging: true,
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
      keys: {
        columns: keyTarget
      },
      pageLength: isEditMode ? -1 : defaultRows,
      select: selectSettings,
      search: {
        return: true
      },
      searchHighlight: true,
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
        let localInstanceSelected = typeof tableState != 'undefined' ? tableState.selected : _data.selected;
        tableState = _data;
        tableState.selected = localInstanceSelected;
        tableState.edit_view = isEditMode;
        // TODO: store editingRows...
      },
      stateLoadParams: function(_settings, _data){
        let localInstanceSelected = typeof tableState != 'undefined' ? tableState.selected : _data.selected;
        tableState = _data;
        tableState.selected = localInstanceSelected;
      },
      buttons: get_available_buttons(),
    });
  }
  initialize_datatable();
}