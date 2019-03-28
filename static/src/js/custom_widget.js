odoo.define('intitec_peru_einvoice_factura.form_widgets', function(require) {
    "use strict";

    var core = require('web.core');
    var form_common = require('web.form_common');
    var FieldChar = core.form_widget_registry.get('char');

    FieldChar.include({
        // this is will be work for all FieldChar in the system
        template: 'it_input_text', // my template for char fields
        // we can create here any logic for render
        //render_value: function() {
        //}
    });
    // this is widget for unique CharField
    var MyModuleFieldChar = FieldChar.extend({
        template: 'ItInputText' // my custom template for unique char field
    });
    // register unique widget, because Odoo does not know anything about it
    core.form_widget_registry.add('It_Input_Text', MyModuleFieldChar);

});