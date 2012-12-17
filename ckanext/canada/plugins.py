import ckan.plugins as p

class DataGCCAPublic(p.SingletonPlugin):

    p.implements(p.IConfigurer)

    def update_config(self, config):
        # add our templates
        p.toolkit.add_template_directory(config, 'templates/public')
        p.toolkit.add_public_directory(config, 'public')
