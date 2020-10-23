var ComponentsBootstrapSelectSplitter = function() {

    var selectSplitter = function() {
        $('#select_selectsplitter1').selectsplitter({
            selectSize: 4
        });
        $('#select_selectsplitter2').selectsplitter({
            selectSize: 6
        });
        $('#select_selectsplitter3').selectsplitter({
            selectSize: 5
        });
    }

    return {
        //main function to initiate the module
        init: function() {
            selectSplitter();
        }
    };

}();

jQuery(document).ready(function() {    
   ComponentsBootstrapSelectSplitter.init(); 
});