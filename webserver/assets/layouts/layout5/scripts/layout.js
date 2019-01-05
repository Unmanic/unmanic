/**
Core script to handle the entire theme and core functions
**/
var Layout = function() {

    var layoutImgPath = 'layouts/layout5/img/';

    var layoutCssPath = 'layouts/layout5/css/';

    var resBreakpointMd = App.getResponsiveBreakpoint('md');

    // handle on page scroll
    var handleHeaderOnScroll = function() {
        if ($(window).scrollTop() > 60) {
            $("body").addClass("page-on-scroll");
        } else {
            $("body").removeClass("page-on-scroll");
        }
    }
    
    // Handles active menu to avoid closing click to content

    // handle go to top button
    var handleGo2Top = function () {       
        var Go2TopOperation = function(){
            var CurrentWindowPosition = $(window).scrollTop();// current vertical position
            if (CurrentWindowPosition > 100) {
                $(".go2top").show();
            } else {
                $(".go2top").hide();
            }
        };

        Go2TopOperation();// call headerFix() when the page was loaded
        if (navigator.userAgent.match(/iPhone|iPad|iPod/i)) {
            $(window).bind("touchend touchcancel touchleave", function(e){
                Go2TopOperation();
            });
        } else {
            $(window).scroll(function() {
                Go2TopOperation();
            });
        }

        $(".go2top").click(function(e) {
            e.preventDefault();
             $("html, body").animate({ scrollTop: 0 }, 600);
        });
    };

    var handleHeaderMenu = function() {
        $('.page-header .navbar-nav > .dropdown-fw, .page-header .navbar-nav > .more-dropdown, .page-header .navbar-nav > .dropdown > .dropdown-menu  > .dropdown').click(function(e) {
            
            if (App.getViewPort().width > resBreakpointMd) {
                if ($(this).hasClass('more-dropdown') || $(this).hasClass('more-dropdown-sub')) {
                    return;
                } else {
                     e.stopPropagation();
                }
            } else {
                e.stopPropagation();
            }
            
            var links = $(this).parent().find('> .dropdown');

            if (App.getViewPort().width < resBreakpointMd) {
                if ($(this).hasClass('open')) {
                    links.removeClass('open');
                } else {
                    links.removeClass('open');
                    $(this).addClass('open');
                    App.scrollTo($(this));
                }
            } else {
                if ($(this).hasClass('more-dropdown'))  {
                    return;
                }
                links.removeClass('open');
                $(this).addClass('open');
                App.scrollTo($(this));
            }
        });

        $('.page-header .navbar-nav .more-dropdown-sub .dropdown-menu, .page-header .navbar-nav .dropdown-sub .dropdown-menu').click(function(){

        });
    };

    // Handles main menu on window resize
    var handleMainMenuOnResize = function() {
        // handle hover dropdown menu for desktop devices only
        var width = App.getViewPort().width;
        var menu = $(".page-header .navbar-nav");
        if (width >= resBreakpointMd && menu.data('breakpoint') !== 'desktop') { 
            menu.data('breakpoint', 'desktop');
            $('[data-hover="extended-dropdown"]', menu).not('.hover-initialized').each(function() { 
                $(this).dropdownHover(); 
                $(this).addClass('hover-initialized'); 
            });
        } else if (width < resBreakpointMd && menu.data('breakpoint') !== 'mobile') {
            menu.data('breakpoint', 'mobile');
            // disable hover bootstrap dropdowns plugin
            $('[data-hover="extended-dropdown"].hover-initialized', menu).each(function() {   
                $(this).unbind('hover');
                $(this).parent().unbind('hover').find('.dropdown-submenu').each(function() {
                    $(this).unbind('hover');
                });
                $(this).removeClass('hover-initialized');    
            });
        }
    };

    return {

        // Main init methods to initialize the layout
        // IMPORTANT!!!: Do not modify the core handlers call order.

        init: function () {            
            handleGo2Top();
            handleHeaderOnScroll();
            handleHeaderMenu();
            handleMainMenuOnResize();
            App.addResizeHandler(handleMainMenuOnResize); // handle main menu on window resize

            // handle minimized header on page scroll
            $(window).scroll(function() {
                handleHeaderOnScroll();
            });
        },

        getLayoutImgPath: function() {
            return App.getAssetsPath() + layoutImgPath;
        },

        getLayoutCssPath: function() {
            return App.getAssetsPath() + layoutCssPath;
        }
    };

}();

jQuery(document).ready(function() {    
   Layout.init(); // init metronic core componets
});