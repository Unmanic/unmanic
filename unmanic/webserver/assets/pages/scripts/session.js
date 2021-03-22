$(".login-with-patreon").click(function (e) {
    // Get unmanic patreon client ID
    $.ajax({
        url: '/api/v1/session/unmanic-patreon-login-url',
        type: 'GET',
        success: function (data) {
            if (data.success) {
                // If query was successful
                // let current_uri = window.location.href;
                let current_uri = window.location.origin + "/dashboard/?ajax=login";
                let uuid = data.uuid;
                let url = data.data.url;
                let form = $('<form action="' + url + '" method="post">' +
                    '<input type="text" name="uuid" value="' + uuid + '" />' +
                    '<input type="text" name="current_uri" value="' + current_uri + '" />' +
                    '</form>');
                console.log(form)
                $('body').append(form);
                form.submit();
            } else {
                // Our query was unsuccessful
                console.error('An error occurred while fetching the patreon client ID.');
            }
        },
        error: function (data) {
            console.error('An error occurred while fetching the patreon client ID.');
        },
    });
});

$(".sponsor-with-patreon").click(function (e) {
    // Get unmanic patreon client ID
    $.ajax({
        url: '/api/v1/session/unmanic-patreon-page',
        type: 'GET',
        success: function (data) {
            if (data.success) {
                // If query was successful
                // Open the Patreon sponsor page in a new tab
                var win = window.open(data.data.sponsor_page, '_blank');
                if (win) {
                    //Browser has allowed it to be opened
                    win.focus();
                } else {
                    //Browser has blocked it
                    alert('Please allow popups for this website');
                }
            } else {
                // Our query was unsuccessful
                console.error('An error occurred while fetching the patreon sponsor page.');
            }
        },
        error: function (data) {
            console.error('An error occurred while etching the patreon sponsor page.');
        },
    });
});
