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
  const defaultSortOrder = [[1, "asc"]];
  const defaultRows = 10;
  const ellipsesLength = 100;  // default 100 ellipses length from ckanext-datatablesview
  const primaryKeys = pd_datatable__primaryKeys;
  const foreignKeys = pd_datatable__foreignKeys;
  const foreignLinks = pd_datatable__foreignLinks;
  const chromoFields = pd_datatable__chromoFields;
  const isEditable = pd_datatable__isEditable;
  const selectAllLabel = pd_datatable__selectAllLabel;
  const colSearchLabel = pd_datatable__colSearchLabel;
  const readLessLabel = pd_datatable__readLessLabel;
  const jumpToPageLabel = pd_datatable__jumpToPageLabel;
  const resetTabelLabel = pd_datatable__resetTabelLabel;
  const fullscreenLabel = pd_datatable__fullscreenLabel;
  const exitFullscreenLabel = pd_datatable__exitFullscreenLabel;
  const fullTableLabel = pd_datatable__fullTableLabel;
  const compactTableLabel = pd_datatable__compactTableLabel;
  const editSingleButtonLabel = pd_datatable__editSingleButtonLabel;
  const countSuffix = pd_datatable__countSuffix;
  const ajaxErrorMessage = pd_datatable__ajaxErrorMessage;
  const editSingleRecordURI = pd_datatable__editSingleRecordURI;
  const editButtonLabel = pd_datatable__editButtonLabel;
  const editRecordsURI = pd_datatable__editRecordsURI;
  const deleteButtonLabel = pd_datatable__deleteButtonLabel;
  const deleteRecordsURI = pd_datatable__deleteRecordsURI;
  const ajaxURI = pd_datatable__ajaxURI;
  const tableLanguage = pd_datatable__tableLanguage;
  const markedRenderer = new marked.Renderer();

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
  let sortOrder = defaultSortOrder;

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
    {"className": "expanders", "orderable": false, "targets": 0},
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
            $(_section).find('span[data-markdown="true"]').show(0);
            setTimeout(function(){
              $(expandElement).show(0);
            }, 285);
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
      let ds_type = chromoFields[_index - colOffset].datastore_type;
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

  function cell_renderer(_data, _type, _row, _meta, _chromo_field){
    // FIXME: any data transormations for masks in _type == 'search'
    if( _type == 'display' ){
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

  for( let i = 0; i < chromoFields.length; i++ ){
    if( typeof chromoFields[i].published_resource_computed_field == 'undefined' || ! chromoFields[i].published_resource_computed_field ){
      let previewClass = '';
      if( typeof chromoFields[i].preview_class != 'undefined' ){
        previewClass = chromoFields[i].preview_class;
      }
      if( primaryKeys.includes(i) ){
        previewClass += ' pd-datatables-primary-key-fixed ';
      }
      availableColumns.push({
        "name": chromoFields[i].datastore_id,
        "className": previewClass,
        "searchable": true,
        "render": function(_data, _type, _row, _meta){
          return cell_renderer(_data, _type, _row, _meta, chromoFields[i]);
        }
      });
    }
  }

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
    let buttonStats = $('#dtprv_wrapper').find('span.pd-datatbales-btn-count');
    if( selectCount > 1 ){
      $(singleSelectButtons).each(function(_index, _button){
        $(_button).addClass('disabled');
        $(_button).attr('disabled', 'disabled');
      });
    }
    if( selectCount > 0 ){
      $(buttonStats).each(function(_index, _button){
        $(_button).html('&nbsp;' + selectCount + countSuffix);
      });
    }else{
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
      // TODO: add aria-labels for expanding...
      // td.dtr-hidden
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

  function set_table_visibility(){
    $('#dtprv').css({'visibility': 'visible'});
    $('table.dataTable').css({'visibility': 'visible'});
    $('.dt-scroll-head').css({'visibility': 'visible'});
    $('#dtprv_wrapper').attr('data-editable', isEditable);
    $('#dtprv_wrapper').attr('data-compact-view', isCompactView);
    if( ! isCompactView ){  // set fake visiility for responsive column
      $('#dtprv_wrapper').find('tr').children('th:first-of-type').css(
        {'width': '50px', 'min-width': '50px', 'max-width': '50px', 'padding': 0, 'visibility': 'hidden'});
      $('#dtprv_wrapper').find('tr').children('td:first-of-type').css(
        {'width': '50px', 'min-width': '50px', 'max-width': '50px', 'padding': 0, 'visibility': 'hidden'});
    }else{
      $('#dtprv_wrapper').find('tr').children('th:first-of-type').css(
        {'width': 'auto', 'min-width': 'auto', 'max-width': 'auto', 'padding': '8px',  'visibility': 'visible'});
      $('#dtprv_wrapper').find('tr').children('td:first-of-type').css(
        {'width': 'auto', 'min-width': 'auto', 'max-width': 'auto', 'padding': '8px',  'visibility': 'visible'});
    }
  }

  function set_row_selects(){
    if( typeof tableState != 'undefined' && typeof tableState.selected != 'undefined' ){
      table.rows(tableState.selected).select();
      check_the_boxes(true, tableState.selected);
    }
  }

  function set_button_states(){
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
    if( tableState.order.length != defaultSortOrder.length || (tableState.order[0][0] != defaultSortOrder[0][0] || tableState.order[0][1] != defaultSortOrder[0][1]) ){
      tableModified = true;
    }
    if( table.page.info().page > 0 ){
      tableModified = true;
    }
    if( table.rows({selected: true})[0].length > 0 ){
      tableModified = true;
    }
    // TODO: remove dt_query??
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

  function fix_blank_ordering(_data){
    if( typeof _data.order != 'undefined' ){
      let _sortOrder = _data.order;
      for( let _i = 0; _i < _data.order.length; _i++ ){
        if( ! _data.order[_i][1] ){
          _sortOrder.splice(_i, 1);
        }
      }
      if( _sortOrder.length == 0 ){
        _data.order = defaultSortOrder;
        sortOrder = defaultSortOrder;
      }
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
    }).on('deselect.CheckBoxes', function(e, dt, type, indexes){
      check_the_boxes(false, indexes);
      if( table.rows({selected: true})[0].length > 0 ){
        table.buttons('resetTableButton:name').enable();
      }else{
        table.buttons('resetTableButton:name').enable(false);
      }
    });
  }

  function bind_keyboard_controls(){
    let _start = isCompactView ? 0 : 1;
    $(document).off('keyup.KeyTable');
    $(document).on('keyup.KeyTable', function(_event){
      if( _event.ctrlKey && _event.keyCode == 13 ){  // CTRL + ENTER
        _event.stopPropagation();
        table.cell(':eq(' + _start + ')').focus();
        $('.dt-scroll-body')[0].scrollTop = 0;
      }
    });
    let orderControls = $('.dt-column-order');
    if( orderControls.length > 0 ){
      $(orderControls).each(function(_index, _orderControl){
        $(_orderControl).off('keydown.KeyTable');
        $(_orderControl).on('keydown.KeyTable', function(_event){
          if( _event.ctrlKey && _event.keyCode == 13 ){  // CTRL + ENTER
            $(_orderControl).blur();
            _event.stopPropagation();
            _event.preventDefault();
          }
        });
      });
    }
    table.off('key.KeyTable');
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
      if( (e.ctrlKey && e.keyCode) == 13 || (oe.ctrlKey && oe.keyCode) ){  // CTRL + ENTER
        e.preventDefault();
        oe.preventDefault();
        return
      }
      if( key == 13 ){  // expand on enter
        e.preventDefault();
        oe.preventDefault();
        if( isCompactView ){
          let _row = $('#dtprv-body-main').find('tr').eq(rowIndex);
          let _rowObj = table.row(_row);
          if( $(_row).hasClass('dtr-expanded') ){
            _rowObj.child.hide();
            $(_row).removeClass('dtr-expanded');
          }else{
            // workaround the datatable api to use default child renderers
            table.settings()[0].responsive._detailsDisplay(_rowObj, false);
          }
        }
      }
      // TODO: control for readmore cells??
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
        $('#dtprv').css({'visibility': 'hidden'});
        $('.dt-scroll-head').css({'visibility': 'hidden'});
        dt.clear().destroy();
        initialize_datatable();
      }
    });

    availableButtons.push({
      name: "resetTableButton",
      text: '<i aria-hidden="true" class="fas fa-sync-alt"></i>&nbsp;' + resetTabelLabel,
      className: 'pd-datatable-btn btn-warning pd-datatable-reset-btn',
      enabled: false,
      action: function(e, dt, node, config){
        $('#dtprv').css({'visibility': 'hidden'});
        $('.dt-scroll-head').css({'visibility': 'hidden'});
        table.rows().deselect();
        isCompactView = true;
        tableState = void 0;
        dt.state.clear();
        dt.clear().destroy();
        initialize_datatable();
      }
    });

    if( isEditable ){
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
      availableButtons.push({
        extend: "selected",
        text: '<i aria-hidden="true" class="fas fa-edit"></i>&nbsp;' + editButtonLabel,
        className: "pd-datatable-btn btn-primary",
        action: function(e, dt, button, config){
          // closing form tag needed for py webtest lib
          let form = $('<form></form>', {
            action : editRecordsURI,
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
          let rows = dt.rows({ selected: true });
          rows.eq(0).each(function(index){
            form.append($('<input>').attr({
              type: 'hidden',
              value: dt.cells(index, pk_cols).data().toArray(),
              name: 'bulk-template'
            }));
          });
          form.appendTo('body').submit();
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

  function draw_callback(_settings){
    $('#dtprv_wrapper').find('#dtprv_failure_message').remove();
    set_table_visibility();
    render_expand_buttons();
    render_selectbox_inputs();
    render_pager_input();
    render_foreign_key_links();
    set_button_states();
    bind_readmore();
    if( uri_filters ){
      render_highlights();
    }
    // TODO: human readable sort order...
    // TODO: fix tab indexing in hidden elements!!!
  }

  function init_callback(){
    set_table_visibility();
    render_table_footer();
    bind_readmore();
    set_row_selects();
    set_button_states();
    if( ! isCompactView ){
      table.columns.adjust();
    }
    bind_table_selects();
    bind_keyboard_controls();
  }

  function initialize_datatable(){
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
        columns: ':not(.dtr-hidden)'
      },
      pageLength: defaultRows,
      select: {
        style: 'multi',
        selector: 'td:not(:first-child)'
      },
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
          if( Object.keys(uri_filters).length > 0 ){
            for(let [_index, _value] of Object.entries(uri_filters)){
              _data['columns'][_index]['search']['value'] = _value;
            }
          }
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
        fix_blank_ordering(_data);
        _data.compact_view = isCompactView;
        tableState = typeof tableState != 'undefined' ? tableState : _data;
      },
      stateLoadParams: function(_settings, _data){
        fix_blank_ordering(_data);
        tableState = typeof tableState != 'undefined' ? tableState : _data;
      },
      buttons: get_available_buttons(),
    });
  }
  initialize_datatable();
}