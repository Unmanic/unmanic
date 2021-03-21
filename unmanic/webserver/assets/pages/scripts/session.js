$(".login-with-patreon").click(function (e) {
    const pateron_authorize_url = "https://www.patreon.com/oauth2/authorize";

    // Get unmanic patreon client ID
    $.ajax({
        url: '/api/v1/session/unmanic-patreon-client-id',
        type: 'GET',
        success: function (data) {
            if (data.success) {
                // If query was successful
                // let current_uri = window.location.href;
                let current_uri = window.location.origin + "/dashboard/?ajax=login";
                let state = {
                    uuid: data.uuid,
                    current_uri: current_uri,
                };
                // Build Patreon login page URL
                let params = {
                    response_type: 'code',
                    client_id: data.data.client_id,
                    redirect_uri: data.data.redirect_uri,
                    state: JSON.stringify(state)
                };
                // Redirect to Patreon login page
                window.location.href = pateron_authorize_url + '?' + $.param(params);
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
