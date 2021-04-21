const reloadPluginFlow = function () {
    let plugin_type, plugin_type_id;
    let template_data = {
        plugins: [],
    };

    $('.plugin-flowchart-details').each(function () {
        plugin_type = $(this).find("input[name=plugin_type]").val();
        plugin_type_id = $(this).find("input[name=plugin_type_id]").val()
        updateFlowchartData(plugin_type, plugin_type_id);
    });

    // Block the plugin flowchart
    App.blockUI({
        target: "#configure-plugin-flow-body",
        boxed: true,
    });
};

const savePluginFlow = function (plugin_type, flow_data) {
    let plugin_flow, position, counter, fromOperator, toOperator, properties, links_length;

    plugin_flow = [];

    position = 'start';
    counter = 0;
    while (position !== 'finish') {
        links_length = 0;
        for (const link_pos in flow_data.links) {
            links_length++;
            fromOperator = flow_data.links[link_pos].fromOperator;
            toOperator = flow_data.links[link_pos].toOperator;

            // Check if this is the position we are looking for
            if (fromOperator == position) {

                if (fromOperator !== 'start') {
                    // Fetch the operator data that this links from
                    properties = flow_data.operators[fromOperator].properties;
                    plugin_flow[counter] = {
                        plugin_id: properties.body,
                        plugin_name: properties.title,
                    };

                    // Increment object counter
                    counter++;
                }

                // Set the next position to search for
                position = toOperator;

                // Start on next loop
                break;
            }
        }
        if (counter > links_length) {
            break;
        }
    }

    let params = {
        plugin_type: plugin_type,
        flow: plugin_flow,
    };

    $.ajax({
        url: '/api/v1/plugins/flow/save',
        type: 'POST',
        dataType: 'json',
        data: JSON.stringify(params),
        success: function (data) {
            if (data.success) {
                // If query was successful
                console.debug('Plugin flow saved.');
            } else {
                // Our query was unsuccessful
                console.error('An error occurred while updating the flow.');
            }
        },
        error: function (data) {
            console.error('An error occurred while updating the flow.');
        },
    });

};

const updateFlowchartData = function (plugin_type, plugin_type_id) {
    let params_query = {
        plugin_type: plugin_type
    };

    $.ajax({
        url: '/api/v1/plugins/flow',
        type: 'POST',
        data: params_query,
        success: function (data) {
            if (data.success) {
                // If query was successful

                setTimeout(function () {
                    drawFlow(plugin_type, plugin_type_id, data.plugin_flow);

                    // Unblock the flowchart body
                    App.unblockUI("#configure-plugin-flow-body")
                }, 500);
            } else {
                // Our query was unsuccessful
                console.error('An error occurred while fetching the flow.');
            }
        },
        error: function (data) {
            console.error('An error occurred while fetching the flow.');
        },
    });
};


const drawFlow = function (plugin_type, plugin_type_id, plugin_flow) {
    // Empty the flowchart
    let flowchart_container = $('#' + plugin_type_id + '_plugin_flowchart_container');
    flowchart_container.html('');

    // Create child element for the flowchart
    flowchart_container.prepend('<div id="' + plugin_type_id + '_flowchart"></div>');
    let $flowchart = $('#' + plugin_type_id + '_flowchart');
    let $container = $flowchart.parent();

    let spacing_left = 280;
    let spacing_top = 80;
    let init_pos_left = 20;
    let init_pos_top = 20;

    let graph_width = $flowchart.width();
    let max_pos_left = graph_width - spacing_left;

    let data = {
        operators: {},
        links: {},
        operatorTypes: {},
    };

    // Add the start flow
    data.operators['start'] = {
        "left": init_pos_left,
        "top": init_pos_top,
        "properties": {
            "title": "Start",
            "body": "start",
            "outputs": {
                "output_0": {
                    "label": "Start"
                }
            },
        },
    };

    let pos_left = 20;
    let pos_top = 20;
    let previous_id = 'start';
    for (let i = 0; i < plugin_flow.length; i++) {
        let cur_flow = plugin_flow[i];

        // Add space to the left position
        pos_left += spacing_left;
        if (pos_left >= max_pos_left) {
            pos_left = init_pos_left;
            pos_top += spacing_top;
        }

        // Add operators
        data.operators[i] = {
            "left": pos_left,
            "top": pos_top,
            "properties": {
                "title": cur_flow.name,
                "body": cur_flow.plugin_id,
                "inputs": {
                    "input_0": {
                        "label": "Runner"
                    }
                },
                "outputs": {
                    "output_0": {
                        "label": "→"
                    }
                },
            },
        };

        // Add links
        data.links[i] = {
            "fromOperator": previous_id,
            "fromConnector": "output_0",
            "fromSubConnector": 0,
            "toOperator": i,
            "toConnector": "input_0",
            "toSubConnector": 0
        };
        previous_id = i;
    }

    // Add the finish flow
    pos_left += spacing_left;
    if (pos_left >= max_pos_left) {
        pos_left = init_pos_left;
        pos_top += spacing_top;
    }
    data.operators['finish'] = {
        "left": pos_left,
        "top": pos_top,
        "properties": {
            "title": "Finish",
            "body": "finish",
            "inputs": {
                "input_0": {
                    "label": "Finish"
                }
            },
        },
    };
    data.links['finish'] = {
        "fromOperator": previous_id,
        "fromConnector": "output_0",
        "fromSubConnector": 0,
        "toOperator": 'finish',
        "toConnector": "input_0",
        "toSubConnector": 0
    };

    // Adjust the height of the flowchart to contain everything
    pos_top += 90;
    $flowchart.css('height', pos_top + "px");

    // Apply the plugin on a standard, empty div...
    $flowchart.flowchart({
        data: data,
    });

    $flowchart.parent().siblings('.plugin_flow_save').click(function () {
        let data = $flowchart.flowchart('getData');
        //$('#flowchart_data').val(JSON.stringify(data, null, 2));
        savePluginFlow(plugin_type, data);
    });

    $flowchart.parent().siblings('.delete_selected_button').click(function () {
        $flowchart.flowchart('deleteSelected');
    });

    $flowchart.siblings('.get_data').click(function () {
        let data = $flowchart.flowchart('getData');
        $('#flowchart_data').val(JSON.stringify(data, null, 2));
    });

    $flowchart.siblings('.delete_selected_button').click(function () {
        $flowchart.flowchart('deleteSelected');
    });

};
