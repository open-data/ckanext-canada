from ckan.lib.cli import CkanCommand


class CanadaCommand(CkanCommand):
    summary = "\nDEPRECATED: use `ckan [-c/--c=<config>] canada` instead.\n"
    usage = "\nDEPRECATED: use `ckan [-c/--c=<config>] canada` instead.\n"

    def command(self):
        """
        \nDEPRECATED: use `ckan [-c/--c=<config>] canada` instead.\n
        """
        return
