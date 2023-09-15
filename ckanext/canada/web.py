# coding=UTF-8

"""WxT Theme helper functions

Consists of functions to typically be used within the WXT Canada templates.
"""

import ckan.lib.helpers as h
import ckan.model as model
import webhelpers.html as html

def link_to_user(user, maxlength=0):
    """ Return the HTML snippet that returns a link to a user.  """
    
    # Do not link to pseudo accounts
    if user in [model.PSEUDO_USER__LOGGED_IN, model.PSEUDO_USER__VISITOR]:
        return user
    if not isinstance(user, model.User):
        user_name = unicode(user)
        user = model.User.get(user_name)
        if not user:
            return user_name
        
    if user:
        _name = user.name if model.User.VALID_NAME.match(user.name) else user.id
        displayname = user.display_name
        if maxlength and len(user.display_name) > maxlength:
            displayname = displayname[:maxlength] + '...'
        return html.tags.link_to(displayname,
                       h.url_for('user.read', id=_name))

def render_new_dataset(template, activity):
    """Return the HTML snippet describing a user creating a new dataset"""
    
    # Provide a html link to the user's page
    actor = link_to_user(activity['user_id'])
    actor = '%s' % actor
    
    # Provide a html link to the new group
    object = h.dataset_link(activity['data']['package'])
    if object:
        object = '%s' % object       
         
    # Build the entire message and return the html. 
    date = '%s' % h.render_datetime(activity['timestamp'])
    template = template.format(actor=actor, date=date, object=object)
    template = '%s %s' % (template, date)
    
    # It is important to return it as a literal or it will be converted to text
    return html.literal(template)
    
def render_new_group(template, activity):
    """Return the HTML snippet describing a user creating a new group"""
    
    # Provide a html link to the user's page
    actor = link_to_user(activity['user_id'])
    actor = '%s' % actor
    
    # Provide a html link to the new group
    object = h.group_link(activity['data']['group'])
    if object:
        object = '%s' % object
    
    # Build the entire message and return the html. 
    date = '%s' % h.render_datetime(activity['timestamp'])
    template = template.format(actor=actor, date=date, object=object)
    template = '%s %s' % (template, date)
    
    # It is important to return it as a literal or it will be converted to text
    return html.literal(template)

                      