import ckan.plugins as p
from ckan.lib.plugins import DefaultDatasetForm

class DataGCCAPublic(p.SingletonPlugin):
    """
    Plugin for public-facing version of data.gc.ca site, aka the "portal"
    This plugin requires the DataGCCAForms plugin
    """
    p.implements(p.IConfigurer)

    def update_config(self, config):
        # add our templates
        p.toolkit.add_template_directory(config, 'templates/public')
        p.toolkit.add_public_directory(config, 'public')

class DataGCCAInternal(p.SingletonPlugin):
    """
    Plugin for internal version of data.gc.ca site, aka the "registry"
    This plugin requires the DataGCCAPublic and DataGCCAForms plugins
    """
    p.implements(p.IConfigurer)

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'templates/internal')


class DataGCCAForms(p.SingletonPlugin, DefaultDatasetForm):
    """
    Plugin for dataset forms for Canada's metadata schema
    """
    p.implements(p.IDatasetForm, inherit=True)

    def update_config(self, config):
        config['package_form'] = 'canada_package_form'

    def package_form(self):
        """Returns a string representing the location of the template
        to be rendered. e.g. 'package/new_package_form.html'.
        """
        # the form has been added to the template directory indicated in the 
        # update_config() method of this class. Therefore, only the file name
        # is used and a sub-directory is not included.
        # **** TO DO ******  Edit this form
        return 'dataset_form.html'

    def is_fallback(self):
        """Returns true iff this provides the fallback behaviour, when 
        no other plugin instance matches a package's type.
        
        There must be exactly one fallback controller definte, any attempt
        to register more than one will throw an exception at startup. 
        
        If there's no fallback registered at startup the 
        ckan.lib.plugins.DefaultDatasetForm is used as the fallback.
        """
        return True
    
    def package_types(self):
        """
        Returns an iterable of package type strings.

        If a request involving a package of one of those types is made, then
        this plugin instance will be delegated to.

        There must only be one plugin registered to each package type.  Any
        attempts to register more than one plugin instance to a given package
        type will raise an exception at startup.
        
        The default value is 'dataset', as in 'http:.../dataset'.
        """
        
        #return ["dataset"]
        return []

    def form_to_db_schema(self):
        """Returns the schema for mapping package data from a form to 
        a format suitable for the database. A schema is a list that describes
        a dataset. See ``ckan.logic.schema``
        """
        schema = ckan_schema.form_to_db_package_schema()
#        schema = package_form_schema()
#        schema.update({
#            'published_by': [unicode],
#            'genre_tags': [convert_to_tags(GENRE_VOCAB)],
#            'composer_tags': [convert_to_tags(COMPOSER_VOCAB)]
#        })
        return schema
        
    def db_to_form_schema(self):
        """Returns the schema for mapping package data from the database 
        into a format suitable for the form (optional)
        """
        # return logic.schema.form_to_db_package_schema()
        #schema = package_form_schema()
        
        schema = ckan_schema.db_to_form_package_schema()
        
#        schema.update({
#            'tags': {
#                '__extras': [keep_extras, free_tags_only]
#            },
#            'genre_tags_selected': [
#                convert_from_tags(GENRE_VOCAB), ignore_missing
#            ],
#            'composer_tags_selected': [
#                convert_from_tags(COMPOSER_VOCAB), ignore_missing
#            ],
#            'published_by': [convert_from_extras, ignore_missing],
#        })
#        schema['groups'].update({
#            'name': [not_empty, unicode],
#            'title': [ignore_missing]
#        })
        return schema        
    
    def check_data_dict(self, data_dict, schema=None):
        """Check if the return data is correct.
        raise a DataError if not.
        """
        return
    
    def setup_template_variables(self, context, data_dict=None):
        """Add variables to c just prior to the template being rendered.
        """
        lib_plugins.DefaultDatasetForm.setup_template_variables(self, context, data_dict)
    
    # Implement these methods if you wish to over-ride the default values of
    # - package/read.html
    # - package/search.html
    # - package/new.html
    # - package/new_package_form.html
    # - package/comments.html
    #
    # def read_template(self):
    # def search_template(self):
    # def new_template(self):
    # def history_template(self):
    # def comments_template(self):

