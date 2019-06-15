
// Set the task to view conversion details on
var viewConversionDetails = function(jobId) {
    // Get conversion details template for this item
    $.get('?ajax=conversionDetails&jobId=' + jobId, function (data) {
        // update the list
        $('#conversion_details').html(data)
    });
}

// Filter completed tasks list
var filterCompletedTasks = function(filter) {
    if (filter === 'all') {
        $('.completed_task').show();
    } else if (filter === 'success') {
        $('.completed_task_success').show();
        $('.completed_task_failure').hide();
    } else if (filter === 'failure') {
        $('.completed_task_success').hide();
        $('.completed_task_failure').show();
    }
}
