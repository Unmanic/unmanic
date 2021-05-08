/* Read remote template file and return the compiled template */
Handlebars.getTemplateFromURL = function (name) {
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
Handlebars.registerHelper('ifEquals', function (arg1, arg2, options) {
    return (arg1 == arg2) ? options.fn(this) : options.inverse(this);
});
Handlebars.registerHelper('breaklines', function (text) {
    text = Handlebars.Utils.escapeExpression(text);
    text = text.replace(/(\r\n|\n|\r)/gm, '<br>');
    return new Handlebars.SafeString(text);
});
Handlebars.registerHelper('bbcode', function (text) {
    let result = XBBCODE.process({
        text: text,
        removeMisalignedTags: false,
        addInLineBreaks: false
    });
    text = result.html.replace(/(\r\n|\n|\r)/gm, '<br>');
    return new Handlebars.SafeString(text);
});
Handlebars.registerHelper('escape_quotes', function (variable) {
    return variable.replace(/(['"])/g, '\\$1');
});
Handlebars.registerHelper('pagination', function (currentPage, pageCount, pageSize, options) {
    let context = {
        pages: [],
    };
    for (let i = 1; i <= pageCount; i++) {
        context.pages.push({
            page: i,
            isCurrent: i === currentPage,
        });
    }

    return options.fn(context);
});
Handlebars.registerHelper('setSelectedOption', function (value, options) {
    var $el = $('<select />').html(options.fn(this));
    $el.find('[value="' + value + '"]').attr({'selected': 'selected'});
    return $el.html();
});