
const toggleCheckboxHiddenInput = function (checkbox_id, hidden_input_id) {
    if ($("#" + checkbox_id).prop("checked")) {
        $("#" + hidden_input_id).val("true");
    } else {
        $("#" + hidden_input_id).val("false");
    }
};
