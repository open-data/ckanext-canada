from pylons import c
import ckan.model as model

ORG_MAY_PUBLISH_KEY = 'publish'
ORG_MAY_PUBLISH_VALUE = 'True'

def may_publish_datasets():
    if c.userobj.sysadmin:
        return True

    for g in c.userobj.get_groups():
        if not g.is_organization:
            continue
        if g.extras.get(ORG_MAY_PUBLISH_KEY) == ORG_MAY_PUBLISH_VALUE:
            return True


def user_organizations(user):
    u = model.User.get(user['name'])
    return u.get_groups(group_type = "organization")