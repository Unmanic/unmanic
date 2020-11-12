const fetchFileBrowserTemplate = function (params, callbackSuccess) {
    const current_path = typeof params.current_path !== 'undefined' ? params.current_path : '/';
    const list_type = typeof params.list_type !== 'undefined' ? params.list_type : 'directories';
    const input_field = typeof params.input_field !== 'undefined' ? params.input_field : 'UNKNOWN';
    const title = typeof params.title !== 'undefined' ? params.title : 'Choose Directory';
    const params_query = {
        "ajax": true,
        "current_path": current_path,
        "list_type": list_type,
        "input_field": input_field,
        "title": title,
    };
    const returnPromise = new $.Deferred();
    // Run our ajax query
    $.ajax({
        url: '/filebrowser/',
        type: 'POST',
        data: params_query,
        error: function (e) {
            console.error("ERROR : ", e);
        },
        complete: function (response) {
            // Execute success callback (if one exists)
            if (typeof callbackSuccess === "function") {
                callbackSuccess(response.responseText);
            }

            returnPromise.resolve(response.responseText);
        }
    });
    return returnPromise.promise();
};

(function ($) {

    const callbackFailure = function () {
        console.debug("Failed to update file browser popup. Check logs for more information.");
    };

    const fetchDirectoryListing = function (current_path, list_type, callbackSuccess, callbackFailure) {
        const params_query = {
            "json": true,
            "current_path": current_path,
            "list_type": list_type,
        };
        const returnPromise = new $.Deferred();
        // Run our ajax query
        $.ajax({
            url: '/filebrowser/',
            type: 'POST',
            data: params_query,
            complete: function (response) {
                // Decode our json
                const data = $.parseJSON(response.responseText);

                if (data.success) {
                    // Execute success callback (if one exists)
                    if (typeof callbackSuccess === "function") {
                        callbackSuccess(data);
                    }

                    returnPromise.resolve(data);

                } else {
                    // Our query was unsuccessful

                    // Execute failure callback (if one exists)
                    if (typeof callbackFailure === "function") {
                        callbackFailure();
                    }
                    returnPromise.reject(data);
                }
            }
        });
        return returnPromise.promise();
    };

    const insertFileBrowserListDirectory = function (list_item) {
        /**
         * Insert a new directory listing to the file browser list
         *
         * @type {string}
         */
        let html_template = `
            <li class="mt-list-item unmanic-file-browser-list-item-folder" onclick="$(this).updateFileBrowser('<list_item.full_path>');">
                <div class="list-icon-container done">
                    <i class="icon-folder"></i>
                    <i class="icon-folder-alt"></i>
                </div>
                <div class="list-item-content">
                    <h3>
                        <a href="javascript:;">
                            <list_item.name>
                        </a>
                    </h3>
                </div>
            </li>
        `;
        html_template = html_template.replace("<list_item.full_path>", list_item.full_path);
        html_template = html_template.replace("<list_item.name>", list_item.name);
        $("#unmanic-file-browser-list-items").append(html_template);
    };

    const insertFileBrowserListFile = function (list_item) {
        /**
         * Insert a new directory listing to the file browser list
         *
         * @type {string}
         */
        let html_template = `
            <li class="mt-list-item unmanic-file-browser-list-item-file" onclick="$(this).updateFileBrowser('<list_item.full_path>');">
                <div class="list-icon-container done">
                    <i class="icon-doc"></i>
                </div>
                <div class="list-item-content">
                    <h3>
                        <a href="javascript:;">
                            <list_item.name>
                        </a>
                    </h3>
                </div>
            </li>
        `;
        html_template = html_template.replace("<list_item.full_path>", list_item.full_path);
        html_template = html_template.replace("<list_item.name>", list_item.name);
        $("#unmanic-file-browser-list-items").append(html_template);
    };

    const updateFileBrowserList = function (data) {
        console.debug("Updating browser popup - " + data);
        $("#unmanic-file-browser-list-items").empty();
        $.each(data, (key, value) => {
            if (key == 'current_path') {
                $('input[name ="unmanic-file-browser-current-path"]').val(value);
                // continue
                return;
            } else if (key == 'directories') {
                $.each(value, (key, value) => {
                    insertFileBrowserListDirectory(value);
                });
                // continue
                return;
            } else if (key == 'files') {
                $.each(value, (key, value) => {
                    insertFileBrowserListFile(value);
                });
                // continue
                return;
            }
        });
    };

    $.fn.updateFileBrowser = function (item) {
        item = typeof item !== 'undefined' ? item : $('input[name ="unmanic-file-browser-current-path"]').val();
        const list_type = $('input[name ="unmanic-file-browser-list-type"]').val();
        console.debug("Running file browser update - Location: " + item + " | List type: " + list_type);
        fetchDirectoryListing(item, list_type, updateFileBrowserList, callbackFailure);
    };

    $.fn.updateInputFromFileBrowser = function () {
        const selected_item = $("#unmanic-file-browser-current-path").val();
        const input_field_name = $('input[name ="unmanic-file-browser-original-input-field"]').val();
        $('input[name ="' + input_field_name + '"]').val(selected_item)
    };
})(jQuery);

const updateFileBrowserHTML = function (data) {
    $("#unmanic-file-browser-body").empty();
    $("#unmanic-file-browser-body").append(data);
    $(this).updateFileBrowser();
};
const generateFileBrowserPopupContent = function (input_field, list_type, title) {
    $("#unmanic-file-browser-body").empty();
    const current_path = $('input[name ="' + input_field + '"]').val();
    const params = {
        current_path: current_path,
        list_type: list_type,
        input_field: input_field,
        title: title,
    };
    const result = fetchFileBrowserTemplate(params, updateFileBrowserHTML);
};
