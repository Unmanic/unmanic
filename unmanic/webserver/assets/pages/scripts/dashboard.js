let $dashWS = {
    timer: null,
    ws: null,
    serverId: null,
};
let wsDashboard = function () {
    // Check if connection exists
    if ($dashWS === undefined || $dashWS.ws === null) {
        // Build WS path
        let loc = window.location, new_uri;
        if (loc.protocol === "https:") {
            new_uri = "wss:";
        } else {
            new_uri = "ws:";
        }
        new_uri += "//" + loc.host + "/dashws";

        // Open WS connection
        $dashWS.ws = new WebSocket(new_uri);
    }

    // Return WS
    return $dashWS.ws;
};

let Dashboard = function () {

    let updateCompletedTasks = function (data) {
        // Create template data
        let template_data = {
            'list_items': data
        };
        // Fetch template and display
        let template = Handlebars.getTemplateFromURL('main/completed-tasks');
        $("div#completed_tasks").html(template(template_data));
    };

    let clearWorkerPieCharts = function () {
        $("#worker_pie_charts").html('<div id="worker_pie_chart_notifications"></div>')
    };

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

            // Write the ffmpeg log if the dom exists (portlet is fullscreen)
            $(group_id + ' .worker-ffmpeg-log').each(function () {
                if (element.idle) {
                    $(this).html('');
                } else {
                    if (element.ffmpeg_log_tail.length) {
                        let lines = element.ffmpeg_log_tail.join("");
                        $(this).html(lines);
                    }
                }
            });

            // Get the current runner
            let currentRunner = 'None';
            $.each(element.runners_info, function (key, value) {
                if (value.status === 'in_progress') {
                    currentRunner = value.name;
                }
            });

            // Update the worker status
            $(group_id + ' .worker-status').each(function () {
                $(this).find('.worker-status-current-runner').text(currentRunner);
                if (element.idle) {
                    $(this).find('.worker-status-state').text('Waiting for another task...');
                    $(this).find('.worker-status-start-time').text('');
                    $(this).find('.worker-status-total-proc-time').text('');
                } else {
                    $(this).find('.worker-status-state').text('Processing task...');
                    let startTime = new Date(element.start_time * 1000);
                    $(this).find('.worker-status-start-time').text(startTime);
                    $(this).find('.worker-status-total-proc-time').text(printTimeSinceDate(startTime));
                }
            });
        };

        const printTimeSinceDate = function(startDate) {
            let date_now = new Date();

            let seconds = Math.floor((date_now - (startDate))/1000);
            let minutes = Math.floor(seconds/60);
            let hours = Math.floor(minutes/60);
            let days = Math.floor(hours/24);

            hours = hours-(days*24);
            minutes = minutes-(days*24*60)-(hours*60);
            seconds = seconds-(days*24*60*60)-(hours*60*60)-(minutes*60);

            return "Days: " + days + " Hours: " + hours + " Minutes: " + minutes + " Seconds: " + seconds;
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
            // When the worker-full-screen button is clicked, make the footer visible
            // This is pinched from app.js and expanded to include hiding and showing the footer elements
            template.find(".worker-full-screen-toggle").on('click', function (e) {
                e.preventDefault();
                let portlet = $(this).closest(".portlet");
                workerToggleFullScreen(portlet);
            });
            // Set portlet tooltips
            template.find(".worker-full-screen-toggle").tooltip({
                container: 'body',
                title: 'Fullscreen'
            });
            template.find(".worker-name").text(element.name);
            // Insert the template into the container
            template.appendTo("#worker_pie_charts");
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

    let workerToggleFullScreen = function (portlet) {
        if (portlet.hasClass('portlet-fullscreen')) {
            // Minimise
            $(this).removeClass('on');
            portlet.removeClass('portlet-fullscreen');
            $('body').removeClass('page-portlet-fullscreen');

            // Hide worker details body
            portlet.children('.portlet-body').html('');
            portlet.children('.portlet-body').css('height', 'auto');
            portlet.children('.portlet-body').addClass('hidden');
            portlet.children('.portlet-title').children('.caption').removeClass('col-md-11');
            portlet.children('.portlet-title').children('.actions').addClass('hidden');
            portlet.children('.portlet-title').find('.worker-chart').removeClass('col-md-6');
            portlet.children('.portlet-title').find('.worker-status').addClass('hidden');
            portlet.children('.portlet-title').find('.worker-subtitle').css('height', '');
            portlet.children('.portlet-body').html('');
        } else {
            // Maximise
            //let height = App.getViewPort().height -
            //    portlet.children('.portlet-title').outerHeight() -
            //    parseInt(portlet.children('.portlet-body').css('padding-top')) -
            //    parseInt(portlet.children('.portlet-body').css('padding-bottom'));

            $(this).addClass('on');
            portlet.addClass('portlet-fullscreen');
            $('body').addClass('page-portlet-fullscreen');

            // Display worker details body
            //portlet.children('.portlet-body').css('height', height);
            portlet.children('.portlet-body').removeClass('hidden');
            portlet.children('.portlet-title').children('.caption').addClass('col-md-11');
            portlet.children('.portlet-title').children('.actions').removeClass('hidden');
            portlet.children('.portlet-title').find('.worker-chart').addClass('col-md-6');
            portlet.children('.portlet-title').find('.worker-status').removeClass('hidden');
            portlet.children('.portlet-title').find('.worker-subtitle').css('height', '25px');
            portlet.children('.portlet-body').html('<div id="worker-details"></div>');

            // Inject worker details template
            let template = Handlebars.getTemplateFromURL('main/worker-details');
            $("div#worker-details").html(template({}));
        }
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
        },

        initDashboardWebsocket: function () {
            let ws = wsDashboard();
            let wsSend = function () {
                ws.send("start_workers_info");
                ws.send("start_completed_tasks_info");
            };
            ws.onopen = function () {
                clearTimeout($dashWS.timer);
                clearWorkerPieCharts();
                wsSend();
            };
            ws.onmessage = function (evt) {
                if (typeof evt.data === "string") {
                    let jsonData = JSON.parse(evt.data);
                    if (jsonData.success) {
                        // Ensure the server is still running the same instance...
                        if ($dashWS.serverId === null) {
                            $dashWS.serverId = jsonData.server_id;
                        } else {
                            if (jsonData.server_id !== $dashWS.serverId) {
                                // Reload the whole page. Some things may have changed
                                console.log('Unmanic server has restarted. Reloading page...')
                                location.reload();
                            }
                        }
                        // Parse data type and update the dashboard
                        switch (jsonData.type) {
                            case 'workers_info':
                                updateWorkerPieCharts(jsonData.data);
                                break;
                            case 'completed_tasks':
                                updateCompletedTasks(jsonData.data);
                                break;
                            default:
                                console.error('WebSocket Error: Received data was not a valid type - ' + jsonData.type);
                                break;
                        }
                    } else {
                        console.error('WebSocket Error: Received contained errors - ' + evt.data);
                    }
                } else {
                    console.error('WebSocket Error: Received data was not JSON - ' + evt.data);
                }
            };
            ws.onerror = function (evt) {
                console.error('WebSocket Error: ' + evt);
                clearWorkerPieCharts();
                App.alert({
                    container: '#worker_pie_chart_notifications',
                    place: 'append',
                    type: 'danger',
                    message: 'Could not update workers. Please check that Unmanic is still running.',
                    close: false,
                    reset: true,
                    focus: false,
                    closeInSeconds: 0,
                    icon: 'warning',
                })
            };
            ws.onclose = function () {
                $dashWS.ws = null;
                $dashWS.timer = setTimeout(() => {
                    console.debug('Attempting reconnect to Unmanic server...');
                    Dashboard.initDashboardWebsocket();
                }, 5000);
            };
        },

        init: function () {
            // Init the widgets
            //this.initSparklineCharts();
            this.initDashboardWebsocket();
        }
    };

}();

if (App.isAngularJsApp() === false) {
    jQuery(document).ready(function () {
        Dashboard.init();
    });
}
