let $dashws;
let wsDashboard = function () {
    // Check if connection exists
    if ($dashws === undefined) {
        // Build WS path
        let loc = window.location, new_uri;
        if (loc.protocol === "https:") {
            new_uri = "wss:";
        } else {
            new_uri = "ws:";
        }
        new_uri += "//" + loc.host + "/dashws";

        // Open WS connection
        $dashws = new WebSocket(new_uri);
    }

    // Return WS
    return $dashws;
};

let Dashboard = function () {

    let updateWorkerPieCharts = function (data) {
        let default_percent_value = 100;
        let default_current_file = 'Waiting for job...';

        let insertData = function (group_id, element) {
            $(group_id + ' .number').each(function () {
                if (element.idle) {
                    // Set graph
                    $(this).data('easyPieChart').options.barColor = App.getBrandColor('yellow');
                    $(this).data('easyPieChart').update(default_percent_value);
                    $('span', this).text('IDLE');
                    // Set subtitle text
                    $(group_id + ' .worker-subtitle').each(function () {
                        $(this).text(default_current_file);
                        $(this).prop('title', '');
                    });
                } else {
                    // Set graph
                    $(this).data('easyPieChart').options.barColor = App.getBrandColor('green');
                    if (typeof element.progress.percent !== 'undefined') {
                        $(this).data('easyPieChart').update(element.progress.percent);
                        $('span', this).text(element.progress.percent + '%');
                    } else {
                        $(this).data('easyPieChart').update(0);
                        $('span', this).text('IDLE');
                    }
                    // Set subtitle text
                    $(group_id + ' .worker-subtitle').each(function () {
                        $(this).text(element.current_file);
                        $(this).prop('title', element.current_file);
                    });
                }
            });
        };

        let addNewChart = function (group_id, element) {
            // Fetch template
            let template = $("#unmanic_worker_piechart_template").clone();
            // Change the ID
            template.attr('id', 'unmanic_worker_' + element.id);
            // Add the worker-pie-chart-item class
            template.addClass('worker-pie-chart-item');
            // Remove the hidden class
            template.removeClass('hidden');
            // Modify the name
            template.find(".worker-name").text(element.name);
            // Insert the template into the container
            template.appendTo( "#worker_pie_charts" );
            // Init the pie charts again to include this new element
            Dashboard.initEasyPieCharts();
            // Update data
            insertData(group_id, element);
        };

        // Create list of ids that should exist
        let element_list = [];
        // Set the class of all .number divs. (active or idle)
        // If the element does not yet exist (a new worker was created) then add it
        data.forEach(function (element) {
            // console.log(element)
            var group_id = "#unmanic_worker_" + element.id;
            element_list.push(group_id);
            if ($(group_id).length) {
                insertData(group_id, element);
            } else {
                addNewChart(group_id, element);
            }
        });
        // If an element exists but it should not, remove it
        $('.worker-pie-chart-item').each(function () {
            if (!element_list.includes('#' + $(this).attr('id'))) {
                // element does not belong
                console.debug("Removing worker - " + $(this).attr('id'));
                $(this).remove()
            }
        });
    };

    return {

        initSparklineCharts: function () {
            if (!jQuery().sparkline) {
                return;
            }
            $("#sparkline_bar").sparkline([8, 9, 10, 11, 10, 10, 12, 10, 10, 11, 9, 12, 11, 10, 9, 11, 13, 13, 12], {
                type: 'bar',
                width: '100',
                barWidth: 5,
                height: '55',
                barColor: '#35aa47',
                negBarColor: '#e02222'
            });

            $("#sparkline_bar2").sparkline([9, 11, 12, 13, 12, 13, 10, 14, 13, 11, 11, 12, 11, 11, 10, 12, 11, 10], {
                type: 'bar',
                width: '100',
                barWidth: 5,
                height: '55',
                barColor: '#ffb848',
                negBarColor: '#e02222'
            });

            $("#sparkline_bar5").sparkline([8, 9, 10, 11, 10, 10, 12, 10, 10, 11, 9, 12, 11, 10, 9, 11, 13, 13, 12], {
                type: 'bar',
                width: '100',
                barWidth: 5,
                height: '55',
                barColor: '#35aa47',
                negBarColor: '#e02222'
            });

            $("#sparkline_bar6").sparkline([9, 11, 12, 13, 12, 13, 10, 14, 13, 11, 11, 12, 11, 11, 10, 12, 11, 10], {
                type: 'bar',
                width: '100',
                barWidth: 5,
                height: '55',
                barColor: '#ffb848',
                negBarColor: '#e02222'
            });

            $("#sparkline_line").sparkline([9, 10, 9, 10, 10, 11, 12, 10, 10, 11, 11, 12, 11, 10, 12, 11, 10, 12], {
                type: 'line',
                width: '100',
                height: '55',
                lineColor: '#ffb848'
            });
        },

        initEasyPieCharts: function () {
            if (!jQuery().easyPieChart) {
                return;
            }

            $('.worker-pie-chart .number.idle').easyPieChart({
                animate: 1000,
                size: 75,
                lineWidth: 3,
                barColor: App.getBrandColor('yellow')
            });

            $('.worker-pie-chart .number.active').easyPieChart({
                animate: 1000,
                size: 75,
                lineWidth: 3,
                barColor: App.getBrandColor('green')
            });

            $('.worker-pie-chart .number.bounce').easyPieChart({
                animate: 1000,
                size: 75,
                lineWidth: 3,
                barColor: App.getBrandColor('red')
            });

            $('.worker-pie-chart-reload').click(function () {
                updateWorkerPieCharts();
            });
        },

        initDashboardWebsocket: function () {
            let ws = wsDashboard();
            ws.onopen = function () {
                ws.send("workers_info");
            };
            ws.onmessage = function (evt) {
                if (typeof evt.data === "string") {
                    let jsonData = JSON.parse(evt.data);
                    if (jsonData.success) {
                        // Parse JSON and send it to update the pie charts
                        updateWorkerPieCharts(jsonData.data);
                    } else {
                        console.error('WebSocket Error: Received contained errors - ' + evt.data);
                    }
                } else {
                    console.error('WebSocket Error: Received data was not JSON - ' + evt.data);
                }
            };
            ws.onerror = function (evt) {
                console.error('WebSocket Error: ' + evt);
            };
            window.setInterval(function () {
                ws.send("workers_info");
            }, 100);
        },

        initHistoricalTasks: function () {
            window.setInterval(function () {
                updateHistoricalTasksList();
            }, 5000);
        },

        init: function () {
            // Init the widgets
            //this.initSparklineCharts();
            this.initDashboardWebsocket();
            this.initHistoricalTasks();
        }
    };

}();

if (App.isAngularJsApp() === false) {
    jQuery(document).ready(function () {
        Dashboard.init();
    });
}
