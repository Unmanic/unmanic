
const makeAjaxPost = function (url, params_query, callbackSuccess) {
    const returnPromise = new $.Deferred();
    // Run our ajax query
    $.ajax({
        url: url,
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
