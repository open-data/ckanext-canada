window.addEventListener('load', function(){
    $(function () {
        $('#publish_all').on('click', function () {
            $('#publish_form').find(':checkbox').prop('checked', this.checked);
        });
    });
});
