import logging
from ckan.lib.base import BaseController, c, render

class CanadaController(BaseController):
    def view_guidelines(self):
        return render('guidelines.html')
        
    def view_help(self):
        return render('help.html')
