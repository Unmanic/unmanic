/**
 Overlay Module
 **/
var AppOverlay = function () {

    var _handleProjectListMenu = function () {
        if (App.getViewPort().width <= 992) {
            $('.todo-project-list-content').addClass("collapse");
        } else {
            $('.todo-project-list-content').removeClass("collapse").css("height", "auto");
        }
    };

    // public functions
    return {

        //main function
        init: function () {
            /* _initComponents(); */
            _handleProjectListMenu();

            App.addResizeHandler(function () {
                _handleProjectListMenu();
            });
        }

    };

}();

jQuery(document).ready(function () {
    AppOverlay.init();
});