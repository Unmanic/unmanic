/**
 * Build a Pending task datatable
 *
 * @param bytes
 * @param decimals
 * @returns {string}
 */
var PeningTasksDatatablesManaged = function () {

    var recordSelectedCheckbox = function (oObj) {
        var row_id = oObj.id;
        var task_label = oObj.task_label;
        return '<input class="" type="checkbox" id="checkbox_' + $.trim(row_id) + '" class="md-check checkboxes" value="' + $.trim(row_id) + '">';
    };

    var datatableInitComplete = function () {

        // When the pending-tasks-fullscreen button is clicked, make the footer visible
        // This is pinched from app.js and expanded to include hiding and showing the footer elements
        $('#pending-tasks-fullscreen').on('click', function (e) {
            e.preventDefault();
            var portlet = $(this).closest(".portlet");
            if (portlet.hasClass('portlet-fullscreen')) {
                $(this).removeClass('on');
                portlet.removeClass('portlet-fullscreen');
                $('body').removeClass('page-portlet-fullscreen');
                portlet.children('.portlet-body').css('height', 'auto');

                // Set table to preview mode
                $('.dashboard-task-list-pending').each(function () {
                    $(this).addClass('dashboard-task-list-preview');
                });

                // Set the table to only show 5 items
                $("div.dataTables_length select").val('5').trigger('change');
            } else {
                var height = App.getViewPort().height -
                    portlet.children('.portlet-title').outerHeight() -
                    parseInt(portlet.children('.portlet-body').css('padding-top')) -
                    parseInt(portlet.children('.portlet-body').css('padding-bottom'));

                $(this).addClass('on');
                portlet.addClass('portlet-fullscreen');
                $('body').addClass('page-portlet-fullscreen');
                portlet.children('.portlet-body').css('height', height);

                // Set the table to default to 20 items
                $("div.dataTables_length select").val('20').trigger('change');

                // Remove table from preview mode
                $('.dashboard-task-list-pending').each(function () {
                    $(this).removeClass('dashboard-task-list-preview');
                });
            }
        });

        // Set portlet tooltips
        $('#pending-tasks-fullscreen').tooltip({
            container: 'body',
            title: 'Fullscreen'
        });

    };

    var handleRecords = function () {

        var grid = new Datatable();

        grid.init({
            src: $("#pending_tasks_table"),
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
                "responsive": false,

                "bStateSave": false, // save datatable state(pagination, sort, etc) in cookie.
                "ajax": {
                    "url": '/api/v1/pending/list', // ajax source
                    "contentType": "application/json",
                },
                "aoColumns": [
                    {
                        mData: null,
                        sName: 0,
                        bSortable: false,
                        bSearchable: false,
                        mRender: recordSelectedCheckbox,
                        sClass: "dataTables_select",
                    },
                    {
                        mData: null,
                        sName: "id",
                        bSortable: false,
                        bSearchable: false,
                        bVisible: false,
                    },
                    {
                        mData: "abspath",
                        sName: "abspath",
                        bSortable: false,
                        bSearchable: true,
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
                    "emptyTable": "There are currently no pending tasks...",
                    "infoEmpty": "<span class='seperator'>|</span><span class='font-sm'>No records found</span>",
                    "search": "Search Name:",
                    "metronicGroupActions": "",
                    "metronicAjaxRequestGeneralError": "Could not update table. Please check that Unmanic is still running.",
                    "zeroRecords": "No matching records found",
                    "paginate": {
                        "previous": "Prev",
                        "next": "Next",
                        "last": "Last",
                        "first": "First"
                    }
                },

                "pagingType": "bootstrap_full_number",

                "sLengthSelect": "pending_tasks_table_footer",

                "lengthMenu": [
                    [5, 10, 20, 50, 100, 500, -1],
                    [5, 10, 20, 50, 100, 500, "All"] // change per page values here
                ],
                "pageLength": 5, // default record count per page
                "order": [
                    [1, "desc"]
                ],// set id as a default sort by asc

                "initComplete": function (settings, json) {
                    datatableInitComplete();

                    // Trigger a refresh of the table every 30 seconds
                    setInterval(function () {
                        // Only refresh when no fullscreen
                        var portlet = $('#pending-tasks-fullscreen').closest(".portlet");
                        if (!portlet.hasClass('portlet-fullscreen')) {
                            grid.getDataTable().ajax.reload();
                        }
                    }, 10000);
                }
            }
        });

        // Pull the filters to the top left above the table
        $('.dataTables_filter').addClass('pull-left');

        // Remove overflow
        //grid.getTableWrapper().css("overflow-x", "hidden");

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

        // Configure button for removing items from the task list
        grid.getTableWrapper().on('click', '.remove-from-task-list', function (e) {
            e.preventDefault();
            processAction('remove-from-task-list');
        });

        // Configure button for moving items to the top of the task list
        grid.getTableWrapper().on('click', '.move-to-top-of-task-list', function (e) {
            e.preventDefault();
            processAction('move-to-top-of-task-list');
        });

        // Configure button for moving items to the bottom of the task list
        grid.getTableWrapper().on('click', '.move-to-bottom-of-task-list', function (e) {
            e.preventDefault();
            processAction('move-to-bottom-of-task-list');
        });

        // Configure button for triggering a rescan of the library
        grid.getTableWrapper().on('click', '.rescan-library', function (e) {
            e.preventDefault();
            $.ajax({
                url: '/api/v1/pending/rescan',
                type: 'GET',
            });
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
    PeningTasksDatatablesManaged.init();
});

