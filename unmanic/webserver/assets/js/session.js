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
                let form = $(
                    '<form action="' + url + '" method="post">' +
                    '<input type="hidden" name="uuid" value="' + uuid + '" />' +
                    '<input type="hidden" name="current_uri" value="' + current_uri + '" />' +
                    '</form>'
                );
                console.debug(form);
                $('body').append(form);
                form.submit();
            } else {
                // Our query was unsuccessful
                console.error('An error occurred while fetching the patreon login url.');
            }
        },
        error: function (data) {
            console.error('An error occurred while fetching the patreon login url.');
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

$(".unmanic-sign-out").click(function (e) {
    // Get unmanic sign out client ID
    $.ajax({
        url: '/api/v1/session/unmanic-sign-out-url',
        type: 'GET',
        success: function (data) {
            if (data.success) {
                // If query was successful
                // let current_uri = window.location.href;
                let current_uri = window.location.origin + "/dashboard/?ajax=login";
                let uuid = data.uuid;
                let url = data.data.url;
                let form = $(
                    '<form action="' + url + '" method="post" class="display:none;">' +
                    '<input type="hidden" name="uuid" value="' + uuid + '" />' +
                    '<input type="hidden" name="current_uri" value="' + current_uri + '" />' +
                    '</form>'
                );
                console.debug(form);
                $('body').append(form);
                form.submit();
            } else {
                // Our query was unsuccessful
                console.error('An error occurred while fetching the sign out form details.');
            }
        },
        error: function (data) {
            console.error('An error occurred while fetching the sign out form details.');
        },
    });
});
