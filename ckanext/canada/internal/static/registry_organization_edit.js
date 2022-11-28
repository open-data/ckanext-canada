window.addEventListener('load', function(){
    $(function () {
        let $field_url = $('#field-name');

        function format_url(en,fr) {
            // return URL in the form en-fr
            let $value_en = (en) ? $.url.slugify(en, true) : '',
                $value_fr = (fr) ? $.url.slugify(fr, true) : '';

            if ($value_en && !$value_fr)
                return $value_en;
            if (!$value_en && $value_fr)
                return $value_fr;
            if ($value_en == $value_fr)
                return $value_en;

            return ($value_en + '-' + $value_fr);
        }

        if (!$field_url.val()) {
            $('#field-shortform-en').on('input', function () {
                $field_url.val(format_url($('#field-shortform-en').val(), $('#field-shortform-fr').val()));
            });
            $('#field-shortform-fr').on('input', function () {
                $field_url.val(format_url($('#field-shortform-en').val(), $('#field-shortform-fr').val()));
        });
        }
    });
});
