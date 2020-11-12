var ComponentsBootstrapSelect = function () {

    var handleBootstrapSelect = function() {
        $('.bs-select').selectpicker({
            iconBase: 'fa',
            tickIcon: 'fa-check'
        });
    }

    return {
        //main function to initiate the module
        init: function () {      
            handleBootstrapSelect();
        }
    };

}();

if (App.isAngularJsApp() === false) {
    jQuery(document).ready(function() {    
        ComponentsBootstrapSelect.init(); 
    });
}