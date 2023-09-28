import click

from ckanext.canada.triggers import update_triggers

def get_commands():
    return [canada]


@click.group()
def canada():
    """Canada management commands.
    """
    pass
