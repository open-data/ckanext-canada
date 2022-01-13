$(function () {
    var $field_en = $('#field-shortform-en'),
        $field_fr = $('#field-shortform-fr'),
        $field_url = $('#field-name');
    if (!$field_url.val()) {
        $field_en.on('input', function () {
            $field_url.val($field_en.val());
        });
        $field_fr.on('input', function () {
            if ($field_en.val() != $field_fr.val()) {
                $field_url.val($field_en.val() + '-' + $field_fr.val());
            } else {
                $field_url.val($field_en.val());
            }
      });
    }
});