/**
 * Build a Plugins datatable
 *
 * @param bytes
 * @param decimals
 * @returns {string}
 */
var PluginsDatatablesManaged = function () {

    var recordSelectedCheckbox = function (oObj) {
        var row_id = oObj.id;
        var task_label = oObj.task_label;
        return '<input class="" type="checkbox" id="checkbox_' + $.trim(row_id) + '" class="md-check checkboxes" value="' + $.trim(row_id) + '">';
    };

    var recordDescription = function (oObj) {
        let html = '';
        let description_text = oObj.description;
        // Limit description text to 280 characters
        if (description_text.length > 280) {
            description_text = description_text.substring(0, 277) + '...';
        }
        // Wrap the description text
        html = '<span>' + description_text + '</span>';
        return html;
    };

    var recordIcon = function (oObj) {
        var html = '<span>' +
            '<a href="javascript:;" onclick="showPluginInfo(\'' + oObj.plugin_id + '\');" class="thumbnail" data-target="#configure-plugin" data-toggle="modal" title="Configure">' +
            '<img src="' + oObj.icon + '" class="plugin-list-icon">' +
            '</a>' +
            '</span>';
        return html;
    };

    var recordUpdateStatus = function (oObj) {
        let enabled_html = '';
        let update_html = '';
        if (oObj.status.enabled) {
            enabled_html = '<span class="label label-sm label-success"> Enabled </span>';
        } else {
            enabled_html = '<span class="label label-sm label-danger"> Disabled </span>';
        }
        if (oObj.status.update) {
            update_html = '<span class="label label-sm label-warning"> update-available </span>';
        } else {
            update_html = '<span class="label label-sm label-primary"> up-to-date </span>';
        }
        return enabled_html + '<br>' + update_html;
    };

    var handleRecords = function () {

        var grid = new Datatable();

        grid.init({
            src: $("#installed_plugins_table"),
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
                    "url": '/api/v1/plugins/installed', // ajax source
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
                        sName: "icon",
                        bSortable: false,
                        bSearchable: false,
                        mRender: recordIcon
                    },
                    {
                        mData: "name",
                        sName: "name",
                        bSortable: false,
                        bSearchable: true,
                    },
                    {
                        mData: null,
                        sName: "description",
                        bSortable: false,
                        bSearchable: false,
                        mRender: recordDescription
                    },
                    {
                        mData: "tags",
                        sName: "tags",
                        bSortable: false,
                        bSearchable: true,
                    },
                    {
                        mData: "author",
                        sName: "author",
                        bSortable: false,
                        bSearchable: true,
                    },
                    {
                        mData: "version",
                        sName: "version",
                        bSortable: false,
                        bSearchable: false,
                    },
                    {
                        mData: null,
                        sName: "status",
                        bSortable: false,
                        bSearchable: false,
                        mRender: recordUpdateStatus
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
                    "search": "Search Plugin:",
                    "metronicGroupActions": "",
                    "zeroRecords": "No matching records found",
                    "paginate": {
                        "previous": "Prev",
                        "next": "Next",
                        "last": "Last",
                        "first": "First"
                    }
                },

                "pagingType": "bootstrap_full_number",

                "sLengthSelect": "",

                "lengthMenu": [
                    [5, 10, 20, 50, 100, 500, -1],
                    [5, 10, 20, 50, 100, 500, "All"] // change per page values here
                ],
                "pageLength": 5, // default record count per page
                "order": [
                    [1, "desc"]
                ],// set id as a default sort by asc
            }
        });

        // Pull the filters to the top left above the table
        $('.dataTables_filter').addClass('pull-left');

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

        $("#enable-selected-plugins").click(function () {
            processAction('enable-selected-plugins');
        });

        $("#disable-selected-plugins").click(function () {
            processAction('disable-selected-plugins');
        });

        $("#update-selected-plugins").click(function () {
            processAction('update-selected-plugins');
        });

        $("#remove-selected-plugins").click(function () {
            processAction('remove-selected-plugins');
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
    PluginsDatatablesManaged.init();

    // Reload plugins datatable when we close the install plugins modal
    $(".add-new-plugins-close").click(function () {
        let table = $('#installed_plugins_table').DataTable();
        table.ajax.reload();
    });

    // Reload the plugins list when we open the install plugins modal
    $("#add_plugins").click(function () {
        reloadPluginInstaller();
    });

    // Set actions for search field
    $("#installable_plugins_search").bind(
        'keyup.DT search.DT input.DT paste.DT cut.DT',
        setPluginsFilter
    ).bind('keypress.DT', function (e) {
        /* Prevent form submission */
        if (e.keyCode == 13) {
            return false;
        }
    });
    $("#installable_plugins_search_btn").click(function () {
        setPluginsFilter();
    });
    $("#installable_plugins_search_reset_btn").click(function () {
        resetPluginsFilter();
    });

    // Set portlet tooltips
    $('#plugins-check-updates').click(function () {
        App.blockUI({
            target: "#plugins-installer-content",
            boxed: !0,
            message: "Checking for updates..."
        });
        checkReposForUpdates(function (data) {
            // Unblock the UI
            App.unblockUI("#plugins-installer-content")
            // Fetch latest plugin list
            fetchCurrentPluginList();
        });
    });
});

const reloadPluginInstaller = function () {
    // Fetch the current repo list and fill the REPOSITORIES portlet
    fetchCurrentRepoList();
    fetchCurrentPluginList();
};

const blockElementByID = function (elem_id) {
    App.blockUI({
        target: "#" + elem_id,
        boxed: !0
    });
};
const unblockElementByID = function (elem_id) {
    App.unblockUI("#" + elem_id)
};

const fillRepoListTextbox = function (repos_list) {
    // Block the textbox
    blockElementByID("repos_list_form");
    // Refill the repo textbox
    $("textarea#repos_list").val('');
    repos_list.forEach(function (repo) {
        let repo_list_textbox = $("textarea#repos_list");
        repo_list_textbox.val(repo_list_textbox.val() + repo.path + '\n');
    });
    // Unblock textbox
    unblockElementByID("repos_list_form")
    console.debug('Repo list textbox populated.');
};

const fetchCurrentRepoList = function () {
    // Block the textbox
    blockElementByID("repos_list_form");

    $.ajax({
        url: '/api/v1/plugins/repos/list',
        type: 'GET',
        success: function (data) {
            if (data.success) {
                // If query was successful
                fillRepoListTextbox(data.repos);
                console.log('Repo list updated.');
            } else {
                // Our query was unsuccessful
                console.error('An error occurred while updating the repo list.');
            }
        },
        error: function (data) {
            console.error('An error occurred while updating the repo list.');
        },
    });
};

const checkReposForUpdates = function (callback) {

    $.ajax({
        url: '/api/v1/plugins/repos/fetch',
        type: 'GET',
        success: function (data) {
            if (data.success) {
                // If query was successful
                console.log('Latest repo data downloaded.');
            } else {
                // Our query was unsuccessful
                console.error('An error occurred while downloading the latest repo data.');
            }
            // Execute success callback (if one exists)
            if (typeof callback === "function") {
                callback(data);
            }
        },
        error: function (data) {
            console.error('An error occurred while downloading the latest repo data.');
        },
    });

};


$('#repos_list_form').submit(function (e) {
    var repos_list_form = $('#repos_list_form');

    // Block the textbox
    blockElementByID("repos_list_form");

    e.preventDefault();

    $.ajax({
        type: repos_list_form.attr('method'),
        url: repos_list_form.attr('action'),
        data: repos_list_form.serializeArray(),
        success: function (data) {
            if (data.success) {
                // If query was successful, process data
                // Refill the repo textbox
                fillRepoListTextbox(data.repos);
                fetchCurrentPluginList();
                checkReposForUpdates();
                console.log('Repo list updated.');
            } else {
                // Our query was unsuccessful
                console.error('An error occurred while submitting the repo list form.');
            }
        },
        error: function (data) {
            console.error('An error occurred while submitting the repo list form.');
        },
    });
});

const fillPluginInfo = function (template_data) {
    // Block the plugin info
    blockElementByID("configure-plugin-body");

    // Empty the current plugin info
    $("div#configure-plugin-body").html('');

    // Fetch template and display
    var template = Handlebars.getTemplate('plugins/plugin-info');
    $("div#configure-plugin-body").html(template(template_data));

    // Unblock element
    unblockElementByID("configure-plugin-body");
    console.debug('Plugin info populated.');
};

const showPluginInfo = function (plugin_id) {
    // Empty the current plugin info
    $("div#configure-plugin-body").html('');

    // Block the plugin info
    blockElementByID("configure-plugin-body");

    let params_query = {
        "plugin_id": plugin_id,
    };

    $.ajax({
        url: '/api/v1/plugins/info',
        type: 'POST',
        data: params_query,
        success: function (data) {
            if (data.success) {
                // If query was successful
                fillPluginInfo(data);
                console.log('Plugin info updated.');
            } else {
                // Our query was unsuccessful
                console.error('An error occurred while updating plugin info.');
            }
        },
        error: function (data) {
            console.error('An error occurred while updating plugin info.');
        },
    });
};

const submitPluginSettings = function () {
    var plugin_settings_form = $('#plugin_settings_form');

    console.log(plugin_settings_form.serializeArray());

    $.ajax({
        type: 'POST',
        url: '/api/v1/plugins/settings/update',
        data: plugin_settings_form.serializeArray(),

        success: function (data) {
            if (data.success) {
                // If query was successful, process data
                console.log('Plugin settings updated.');
            } else {
                // Our query was unsuccessful
                console.error('An error occurred while submitting the plugin settings form.');
            }
        },
        error: function (data) {
            console.error('An error occurred while submitting the plugin settings form.');
        },
    });
};

const fillPluginListItems = function (template_data) {
    // Block the plugin list
    blockElementByID("installable_plugins_list");

    // Empty the current list
    $("div#installable_plugins_list").html('');

    // Fetch template and display
    var template = Handlebars.getTemplate('plugins/plugins-list');
    $("div#installable_plugins_list").html(template(template_data));

    // Unblock textbox
    unblockElementByID("installable_plugins_list");
    console.debug('Plugin list populated.');
};

const fetchCurrentPluginList = function () {
    // Block the plugin list
    blockElementByID("installable_plugins_list");

    $.ajax({
        url: '/api/v1/plugins/list',
        type: 'GET',
        success: function (data) {
            if (data.success) {
                // If query was successful
                fillPluginListItems(data);
                console.log('Plugin list updated.');
            } else {
                // Our query was unsuccessful
                console.error('An error occurred while updating the plugin list.');
            }
        },
        error: function (data) {
            console.error('An error occurred while updating the plugin list.');
        },
    });
};

const setPluginsFilter = function () {
    let input, filter, installable_plugins_list, installable_plugins_list_item, plugin_id, plugin_name, plugin_author;

    // Get search filter
    input = $("#installable_plugins_search");
    filter = input.val().toUpperCase();

    // Get all listed plugins
    installable_plugins_list = $("#installable_plugins_list");
    installable_plugins_list_item = installable_plugins_list.find('.installable_plugins_list_item');

    installable_plugins_list_item.each(function () {
        plugin_id = $(this).find(".plugin_id").first();
        plugin_name = $(this).find(".plugin_name").first();
        plugin_author = $(this).find(".plugin_author").first();

        if (plugin_id.text().toUpperCase().indexOf(filter) > -1) {
            $(this).removeClass("hidden")
        } else if (plugin_name.text().toUpperCase().indexOf(filter) > -1) {
            $(this).removeClass("hidden")
        } else if (plugin_author.text().toUpperCase().indexOf(filter) > -1) {
            $(this).removeClass("hidden")
        } else {
            $(this).addClass("hidden");
        }
    });
};

const resetPluginsFilter = function () {
    $("#installable_plugins_search").val('');
    $("#installable_plugins_list").find('.installable_plugins_list_item').each(function () {
        $(this).removeClass("hidden")
    });
};

const downloadPlugin = function (plugin_id, item_number) {
    console.log("Downloading: " + plugin_id);
    // Block the plugin list item

    //blockElementByID("installable_plugins_list_item_" + item_number);
    App.blockUI({
        target: "#installable_plugins_list_item_" + item_number,
        overlayColor: "none",
        animate: !0
    });

    let params_query = {
        "plugin_id": plugin_id,
    };

    $.ajax({
        url: '/api/v1/plugins/install',
        type: 'POST',
        data: params_query,
        success: function (data) {
            if (data.success) {
                // If query was successful
                console.log('Plugin installed.');
            } else {
                // Our query was unsuccessful
                console.error('An error occurred while installing the plugin: "' + plugin_id + '".');
            }
            App.unblockUI("#installable_plugins_list_item_" + item_number);
        },
        error: function (data) {
            console.error('An error occurred while installing the plugin: "' + plugin_id + '".');
            App.unblockUI("#installable_plugins_list_item_" + item_number);
        },
    });
};
