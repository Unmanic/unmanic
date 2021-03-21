/* Read remote template file and return the compiled template */
Handlebars.getTemplate = function (name) {
    if (Handlebars.templates === undefined || Handlebars.templates[name] === undefined || UNMANIC_VERSION === "UNKNOWN") {
        $.ajax({
            url: '/assets/templates/' + name + '.hbs?version=' + UNMANIC_VERSION,
            success: function (data) {
                if (Handlebars.templates === undefined) {
                    Handlebars.templates = {};
                }
                Handlebars.templates[name] = Handlebars.compile(data);
            },
            async: false
        });
    }
    return Handlebars.templates[name];
};

/* HELPERS: */
Handlebars.registerHelper('ifEquals', function(arg1, arg2, options) {
    return (arg1 == arg2) ? options.fn(this) : options.inverse(this);
});
