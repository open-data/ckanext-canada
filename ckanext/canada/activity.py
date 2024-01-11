import ckan.logic as logic
import ckan.lib.dictization.model_dictize as model_dictize
from ckan.plugins.toolkit import side_effect_free


@logic.validate(logic.schema.default_dashboard_activity_list_schema)
@side_effect_free
def recently_changed_packages_activity_list(context, data_dict):
    '''Copied from ckan/ckan/logic/action/get.py

    (canada fork only): Sets `include_data` to True
                        and uses `side_effect_free`

    TODO: Remove this action override in CKAN 2.10 upgrade

    Return the activity stream of all recently added or changed packages.

    :param offset: where to start getting activity items from
        (optional, default: ``0``)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: ``31`` unless set in site's configuration
        ``ckan.activity_list_limit``, upper limit: ``100`` unless set in
        site's configuration ``ckan.activity_list_limit_max``)
    :type limit: int

    :rtype: list of dictionaries

    '''
    # FIXME: Filter out activities whose subject or object the user is not
    # authorized to read.
    model = context['model']
    offset = data_dict.get('offset', 0)
    data_dict['include_data'] = True
    limit = data_dict['limit']  # defaulted, limited & made an int by schema

    activity_objects = \
        model.activity.recently_changed_packages_activity_list(
            limit=limit, offset=offset)

    return model_dictize.activity_list_dictize(
        activity_objects, context,
        include_data=data_dict['include_data'])
