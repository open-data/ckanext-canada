import ckan.plugins as p
from ckan.lib.plugins import DefaultDatasetForm

class DataGCCAPublic(p.SingletonPlugin):
    """
    Plugin for public-facing version of data.gc.ca site
    """
    p.implements(p.IConfigurer)

    def update_config(self, config):
        # add our templates
        p.toolkit.add_template_directory(config, 'templates/public')
        p.toolkit.add_public_directory(config, 'public')

class DataGCCAForms(p.SingletonPlugin, DefaultDatasetForm):
    """
    Plugin for dataset entry forms for internal site
    """
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IDatasetForm, inherit=True)

    def update_config(self, config):
        config['package_form'] = 'canada_package_form'
        p.toolkit.add_template_directory(config, 'templates/internal')

    def package_form(self):
        return "forms/canada_dataset_form.html"
