import logging
from ckan.lib.base import BaseController, c, render, model, request, h
from ckan.logic import get_action, NotAuthorized, check_access
from ckan.lib.helpers import Page
from ckanext.canada.tools import normalize_strip_accents

class CanadaController(BaseController):
    def view_guidelines(self):
        return render('guidelines.html')

    def view_help(self):
        return render('help.html')

    def view_new_user(self):
        return render('newuser.html')

    def organization_index(self):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True,
                   'with_private': False}

        data_dict = {'all_fields': True}

        try:
            check_access('site_read', context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        # pass user info to context as needed to view private datasets of
        # orgs correctly
        if c.userobj:
            context['user_id'] = c.userobj.id
            context['user_is_admin'] = c.userobj.sysadmin

        results = get_action('organization_list')(context, data_dict)

        def org_key(org):
            title = org['title'].split(' | ')[-1 if c.language == 'fr' else 0]
            return normalize_strip_accents(title)

        results.sort(key=org_key)

        c.page = Page(
            collection=results,
            page=request.params.get('page', 1),
            url=h.pager_url,
            items_per_page=1000
        )
        return render('organization/index.html')
