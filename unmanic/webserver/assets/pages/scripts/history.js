var $state = {};

/**
 * Set the task to view conversion details on
 *
 * @param jobId
 * @param rowId
 */
var viewConversionDetails = function (jobId) {
    $state.jobId = jobId;
    // Get conversion details template for this item
    $.get('?ajax=conversionDetails&jobId=' + jobId, function (data) {
        // update/set the conversion details list
        $('#conversion_details').html(data);

        // Highlight the currently selected task
        $('.completed_task').css('background', ''); // Remove highlight on all rows
        $('.completed_task_jobid_' + jobId).css('background', 'rgba(197, 185, 107, 0.20)');
    });
};

/**
 * Reload the completed task list.
 */
var reloadCompletedTaskList = function () {
    var jobId = (typeof $state.jobId !== 'undefined') ? $state.jobId : 0;
    // Get conversion details template for this item
    $.get('?ajax=reloadCompletedTaskList&jobId=' + jobId, function (data) {
        // update/set the conversion details list
        $('#completed_tasks').html(data);
        jQuery(document).ready(function () {
            TableDatatablesManaged.init();
        });
    });
};

/**
 * Filter completed tasks list
 *
 * @param filter
 */
var filterCompletedTasks = function (filter) {
    if (filter === 'all') {
        $('.completed_task').show();
    } else if (filter === 'success') {
        $('.completed_task_success').show();
        $('.completed_task_failure').hide();
    } else if (filter === 'failure') {
        $('.completed_task_success').hide();
        $('.completed_task_failure').show();
    }
};

/**
 * Format a byte integer into the smallest possible number appending a suffix
 *
 * @param bytes
 * @param decimals
 * @returns {string}
 */
var formatBytes = function (bytes, decimals) {
    decimals = (typeof decimals !== 'undefined') ? decimals : 2;
    if (bytes === 0) return '0 Bytes';
    var k = 1024;
    var dm = decimals < 0 ? 0 : decimals;
    var sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    var i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

/**
 *
 */
var addSelectedCompletedTasksToPendingTasksList = function () {
    var table = $("#history_completed_tasks_table");
    var count = table.rows({selected: true}).count();
    console.log(count)
};


var CompletedTasksDatatablesManaged = function () {

    var emptySpan = function (oObj) {
        return '<span></span>';
    };
    var recordNameCellContents = function (task_label) {
        //return '<span style="margin-left: 20px;" class="hidden-xs">' + $.trim(task_label) + '<span>';
        return '<span style="margin-left: 20px;" class="">' + $.trim(task_label) + '<span>';
    };
    var recordSelectedCheckbox = function (oObj) {
        var row_id = oObj.id;
        var task_label = oObj.task_label;
        return '<input class="" type="checkbox" id="checkbox_' + $.trim(row_id) + '" class="md-check checkboxes" value="' + $.trim(row_id) + '">';
        /*return '<input class="hidden-xs hidden-sm" type="checkbox" id="checkbox_' + $.trim(row_id) + '" class="md-check checkboxes">' +
            '<span style="margin-left: 20px;" class="text-left visible-xs hidden-md">' + $.trim(task_label) + '<span>';*/
    };
    var recordSuccessStatus = function (oObj) {
        var html = '';
        if (oObj.task_success) {
            html = '<span class="label label-sm label-success"> Success </span>';
        } else {
            html = '<span class="label label-sm label-danger"> Failed </span>';
        }
        return html;
    };
    var recordActionButton = function (oObj) {
        var row_id = oObj.id;
        return '<a data-toggle="modal" href="#todo-task-modal" class="btn blue m-icon-big" ' +
            'onclick="viewConversionDetails(' + $.trim(row_id) + ');"> View details\n' +
            '<i class="m-icon-swapright m-icon-white"></i>\n' +
            '</a>';
    };

    var handleRecords = function () {

        var grid = new Datatable();

        grid.init({
            src: $("#history_completed_tasks_table"),
            onSuccess: function (grid, response) {
                // grid:        grid object
                // response:    json object of server side ajax response
                // execute some code after table records loaded
            },
            onError: function (grid) {
                // execute some code on network or other general error
            },
            onDataLoad: function (grid) {
                // execute some code on ajax data load
            },
            loadingMessage: 'Loading...',
            dataTable: { // here you can define a typical datatable settings from http://datatables.net/usage/options

                // Uncomment below line("dom" parameter) to fix the dropdown overflow issue in the datatable cells. The default datatable layout
                // setup uses scrollable div(table-scrollable) with overflow:auto to enable vertical scroll(see: assets/global/scripts/datatable.js).
                // So when dropdowns used the scrollable div should be removed.
                //"dom": "<'row'<'col-md-8 col-sm-12'pli><'col-md-4 col-sm-12'<'table-group-actions pull-right'>>r>t<'row'<'col-md-8 col-sm-12'pli><'col-md-4 col-sm-12'>>",
                //"dom": "<'row'<'col-md-6 col-sm-12'l><'col-md-6 col-sm-12'f>r>t<'row'<'col-md-5 col-sm-12'i><'col-md-7 col-sm-12'p>>",
                //"dom": "<'row'<'col-md-8 col-sm-12'li><'col-md-4 col-sm-12'f>r>t<'row'<'col-md-8 col-sm-12'li><'col-md-4 col-sm-12'p>>",
                "dom": "" +
                    "<'row'" +
                        "<'col-md-6 col-sm-12'" +
                            "<'row'" +
                                "<'col-md-12 col-sm-12'" +
                                    "f" +
                                ">" +
                                "<'col-md-12 col-sm-12'" +
                                    "li" +
                                ">" +
                            ">" +
                        ">" +
                        "<'col-md-6 col-sm-12'" +
                            "<'row'" +
                                "<'col-md-12 col-sm-12'" +
                                    "" +
                                ">" +
                                "<'col-md-12 col-sm-12'" +
                                    "<'table-group-actions pull-right'>" +
                                ">" +
                            ">" +
                        ">" +
                        "r" +
                    ">" +
                    "<'row'" +
                        "<'col-md-12 col-sm-12'" +
                            "t" +
                        ">" +
                    ">" +
                    "<'row'" +
                        "<'col-md-8 col-sm-12'" +
                            "li" +
                        ">" +
                        "<'col-md-4 col-sm-12'" +
                            "p" +
                        ">" +
                    ">" +
                "",
                "responsive": true,

                "bStateSave": true, // save datatable state(pagination, sort, etc) in cookie.
                "ajax": {
                    "url": '/api/v1/history/list', // ajax source
                    "contentType": "application/json",
                },
                "aoColumns": [
                    {
                        mData: null,
                        "sName": 0,
                        bSortable: false,
                        bSearchable: false,
                        mRender: recordSelectedCheckbox,
                        sClass: ""
                    },
                    {
                        mData: "task_label",
                        sName: 1,
                        bSortable: true,
                        bSearchable: true
                    },
                    {
                        mData: "finish_time",
                        sName: 2,
                        bSortable: true
                    },
                    {
                        mData: null,
                        sName: 3,
                        bSortable: false,
                        bSearchable: false,
                        mRender: recordSuccessStatus
                    },
                    {
                        mData: null,
                        sName: 4,
                        bSortable: false,
                        bSearchable: false,
                        mRender: recordActionButton
                    },
                ],

                // Internationalisation. For more info refer to http://datatables.net/manual/i18n
                "language": {
                    "aria": {
                        "sortAscending": ": activate to sort column ascending",
                        "sortDescending": ": activate to sort column descending"
                    },
                    "lengthMenu": "<span class='font-sm'>View _MENU_ records</span>",
                    "info": "<span class='seperator'>|</span><span class='font-sm'>Found total _TOTAL_ records</span>",
                    "emptyTable": "No data available in table",
                    "infoEmpty": "<span class='seperator'>|</span><span class='font-sm'>No records found</span>",
                    "search": "Search Name:",
                    "zeroRecords": "No matching records found",
                    "paginate": {
                        "previous": "Prev",
                        "next": "Next",
                        "last": "Last",
                        "first": "First"
                    }
                },

                "pagingType": "bootstrap_full_number",

                "lengthMenu": [
                    [5, 10, 20, 50, 100, 500, -1],
                    [5, 10, 20, 50, 100, 500, "All"] // change per page values here
                ],
                "pageLength": 10, // default record count per page
                "order": [
                    [2, "desc"]
                ]// set first column as a default sort by asc
            }
        });

        $('.dataTables_filter').addClass('pull-left');

        // Remove overflow
        grid.getTableWrapper().css("overflow-x", "hidden");

        var processAction = function (action) {
            if (grid.getSelectedRowsCount() > 0) {
                grid.setAjaxParam("customActionType", "group_action");
                grid.setAjaxParam("customActionName", action);
                grid.setAjaxParam("id", grid.getSelectedRows());
                grid.getDataTable().ajax.reload();
                grid.clearAjaxParams();
            } else {
                App.alert({
                    type: 'danger',
                    icon: 'warning',
                    message: 'No record selected',
                    container: grid.getTableWrapper(),
                    place: 'prepend'
                });
            }
        };
        grid.getTableWrapper().on('click', '.add-to-pending', function (e) {
            e.preventDefault();
            console.debug(grid.getSelectedRows());
            processAction('add-to-pending');
        });
        grid.getTableWrapper().on('click', '.delete-from-history', function (e) {
            e.preventDefault();
            console.debug(grid.getSelectedRows());
            processAction('delete-from-history');
        });

        grid.setAjaxParam("customActionType", "group_action");
        grid.getDataTable().ajax.reload();
        grid.clearAjaxParams();
    };

    return {

        //main function to initiate the module
        init: function () {

            handleRecords();
        }

    };

}();

jQuery(document).ready(function () {
    CompletedTasksDatatablesManaged.init();
});

