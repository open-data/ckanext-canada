"""
Filter scripts are not part of the installed ckanext-canada module.
We're assuming a source install and redirecting the import to run tests.
"""
import os
import sys

bin_filter_path = os.path.join(
    os.path.dirname(str(__file__)),
    '../../../bin/filter')

sys.path.append(bin_filter_path)
import filter_service_std
import filter_contracts
sys.path.pop()

sys.modules.pop('filter_service_std')
sys.modules.pop('filter_contracts')
