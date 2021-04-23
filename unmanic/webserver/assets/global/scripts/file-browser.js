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
            url: '/api/v1/filebrowser/list',
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

    const updateFileBrowserList = function (data) {

        // Fetch template and display updated directory list
        let template = Handlebars.getTemplateFromURL('global/file-browser-file-list');
        let render_template = template(data);
        $("div#unmanic-file-browser-list-items").html(render_template);

        // Update the current path text input
        $('input[name ="unmanic-file-browser-current-path"]').val(data.current_path);
    };

    $.fn.updateFileBrowser = function (item) {
        item = typeof item !== 'undefined' ? item : $('input[name ="unmanic-file-browser-current-path"]').val();
        const list_type = $('input[name ="unmanic-file-browser-list-type"]').val();
        fetchDirectoryListing(item, list_type, updateFileBrowserList, callbackFailure);
    };

    $.fn.updateInputFromFileBrowser = function () {
        const selected_item = $("#unmanic-file-browser-current-path").val();
        const input_field_name = $('input[name ="unmanic-file-browser-original-input-field"]').val();
        $('input[name ="' + input_field_name + '"]').val(selected_item)
    };
})(jQuery);

const generateFileBrowserPopupContent = function (input_field, list_type, title) {
    $("#unmanic-filebrowser-popup").empty();
    const current_path = $('input[name ="' + input_field + '"]').val();
    const params = {
        current_path: current_path,
        list_type: list_type,
        input_field: input_field,
        title: title,
    };
    let template = Handlebars.getTemplateFromURL('global/file-browser-popup');
    let render_template = template(params);
    $("div#unmanic-filebrowser-popup").html(render_template);

    $(this).updateFileBrowser();
};
