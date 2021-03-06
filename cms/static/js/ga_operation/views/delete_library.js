;(function (define) {

    'use strict';
    define(['jquery', 'backbone', 'js/ga_operation/views/ga_base'], function ($, Backbone, GaBaseView) {

        return GaBaseView.extend({
            events: {
                'click #delete_library': 'clickDeleteLibrary'
            },
            clickDeleteLibrary: function (event) {
                if (window.confirm('本当に削除しますか？\nこの操作は取り消せません。')) {
                    this.post(event, 'delete_library');
                } else {
                    window.alert('キャンセルされました');
                }
            }
        });
    });

})(define || RequireJS.define);
