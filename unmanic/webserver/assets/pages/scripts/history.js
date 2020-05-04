
var $state = {};

/**
 * Set the task to view conversion details on
 *
 * @param jobId
 * @param rowId
 */
var viewConversionDetails = function(jobId) {
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
var reloadCompletedTaskList = function() {
    var jobId = (typeof $state.jobId !== 'undefined') ? $state.jobId : 0;
    // Get conversion details template for this item
    $.get('?ajax=reloadCompletedTaskList&jobId=' + jobId, function (data) {
        // update/set the conversion details list
        $('#completed_tasks').html(data);
    });
};

/**
 * Filter completed tasks list
 *
 * @param filter
 */
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

