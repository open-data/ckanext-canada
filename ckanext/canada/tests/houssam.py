import tempfile

# f = tempfile.NamedTemporaryFile(suffix='xlsx')
# file_path = tempfile.TemporaryDirectory() + '/empty_file.xlsx'
f = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
print(f.name)