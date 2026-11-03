import json
import urllib.request
import urllib.error

from pathlib import Path
from urllib.parse import quote

from packaging.version import Version
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.requirements import Requirement, InvalidRequirement

TARGET_PYTHON = Version('3.9.2')
AUDIT_FILE = Path('pip-audit.json')
REQUIREMENTS_FILE = Path('requirements-security-patch.txt')
CKAN_REQUIREMENTS_FILE = Path('/srv/app/src/ckan/requirements.txt')
CHANGELOG_FILE = Path('pip-changes.txt')
SLACK_FILE = Path('pip-slack.json')
EXCLUDED_PACKAGES = {
    canonicalize_name('pkg-resources'),
}
METADATA_CACHE = {}

packages = {}
audit = json.loads(AUDIT_FILE.read_text())
changelog = ['New security patches from pip-audit', '',
             f'Target Python version: {TARGET_PYTHON}', '']
slack_reports = {}


def load_ckan_pins(requirements_file):
    pins = {}
    if not requirements_file.is_file():
        raise FileNotFoundError(f'CKAN requirements file '
                                f'not found: {requirements_file}')
    for line_number, raw_line in enumerate(requirements_file.read_text().splitlines(),
                                           start=1):
        line = raw_line.strip()
        if not line or line.startswith('#') or line.startswith('-'):
            continue
        requirement_text = line.split('#', 1)[0].strip()
        try:
            requirement = Requirement(requirement_text)
        except InvalidRequirement:
            continue
        package = canonicalize_name(requirement.name)
        exact_pins = [
            spec.version
            for spec in requirement.specifier
            if spec.operator == '==' and '*' not in spec.version
        ]
        if len(exact_pins) != 1:
            continue
        version = exact_pins[0]
        if package in pins and pins[package][1] != version:
            raise ValueError('Conflicting CKAN pins for '
                             f'{requirement.name} at line {line_number}')
        pins[package] = (requirement.name, version)
    return pins


ckan_pins = load_ckan_pins(CKAN_REQUIREMENTS_FILE)


def add_email_report_entry(name, installed_version, reasons, vulnerability=None):
    if name not in slack_reports:
        slack_reports[name] = {'installed_version': installed_version,
                               'reasons': reasons,
                               'vulnerabilities': []}

    if vulnerability:
        slack_reports[name]['vulnerabilities'].append({
            'id': vulnerability.get('id', 'Unknown ID'),
            'fix_versions': vulnerability.get('fix_versions', [])
        })


def get_requires_python(name, version):
    key = (canonicalize_name(name), str(version))
    if key in METADATA_CACHE:
        return METADATA_CACHE[key]
    url = f'https://pypi.org/pypi/{quote(name, safe="")}' + \
        f'/{quote(str(version), safe="")}/json'

    try:
        request = urllib.request.Request(
            url, headers={'User-Agent': 'CKAN-Security-Audit/1.0'})
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read())
        result = data.get('info', {}).get('requires_python')
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        print(f'WARNING: Could not retrieve {name}=={version}: {exc}')
        result = None
    METADATA_CACHE[key] = result
    return result


def supports_python(name, version):
    requires_python = get_requires_python(name, version)
    if requires_python is None:
        return None
    try:
        return TARGET_PYTHON in SpecifierSet(requires_python)
    except Exception:
        return None


def select_fix_version(installed_version, candidates):
    if not candidates:
        return None
    installed = Version(installed_version)
    same_branch = [
        version for version in candidates
        if version.release[:2] == installed.release[:2]
    ]
    if same_branch:
        return min(same_branch)
    return min(candidates)


if REQUIREMENTS_FILE.exists():
    for line_number, raw_line in enumerate(REQUIREMENTS_FILE.read_text().splitlines(),
                                           start=1):
        line = raw_line.strip()
        if not line or line.startswith('#') or line.startswith('-'):
            continue
        requirement_text = line.split('#', 1)[0].strip()
        if not line or line.startswith('#') or '==' not in line:
            continue
        name, version = requirement_text.split('==', 1)
        package_key = canonicalize_name(name)
        if package_key in EXCLUDED_PACKAGES or package_key.startswith('ckanext-'):
            continue
        try:
            parsed_version = Version(version)
        except Exception:
            print(f'WARNING: Invalid version: {requirement_text}')
            continue
        compatible = supports_python(name, parsed_version)
        if compatible is False:
            print(f'REMOVED: {name}=={version} (incompatible '
                  f'with Python {TARGET_PYTHON})')
            continue
        if compatible is None:
            print(f'WARNING: Could not verify Python '
                  f'compatibility for {name}=={version}')
            continue
        packages[package_key] = {'name': name, 'version': parsed_version}

for dependency in audit.get('dependencies', []):
    name = dependency['name']
    installed_version = dependency.get('version')
    if name in EXCLUDED_PACKAGES or name.startswith('ckanext-'):
        continue
    if not installed_version:
        print(f'WARNING: Skipping {name}: no installed version in audit results')
        continue
    package_key = canonicalize_name(name)
    if package_key in EXCLUDED_PACKAGES or package_key.startswith('ckanext-'):
        continue
    vulnerabilities = dependency.get('vulns') or []
    if not vulnerabilities:
        continue
    ckan_detail = ''
    if package_key in ckan_pins:
        ckan_name, ckan_version = ckan_pins[package_key]
        ckan_detail = 'CKAN 2.10 pins this dependency to ' + \
            f'`{ckan_name}=={ckan_version}`. Vulnerability remains unresolved.'
    package_fixes = []
    for vuln in vulnerabilities:
        vuln_id = vuln['id']
        fix_versions = vuln.get('fix_versions') or []
        compatible = []
        incompatible = []
        unknown = []
        for fix in fix_versions:
            try:
                version = Version(fix)
            except Exception:
                continue
            result = supports_python(name, version)
            if result is True:
                compatible.append(version)
            elif result is False:
                incompatible.append(version)
            else:
                unknown.append(version)
        details = []
        if compatible:
            details.append('Python 3.9 compatible: ' +
                           ', '.join(map(str, sorted(compatible))))
        if incompatible:
            incompatible_details = []
            for version in sorted(incompatible):
                requires_python = get_requires_python(name, version)
                incompatible_details.append(
                    f'{version} (requires Python {requires_python})')
            details.append('requires newer Python: ' + ', '.join(incompatible_details))
        if unknown:
            details.append('compatibility unknown: ' +
                           ', '.join(map(str, sorted(unknown))))
        if package_key in ['ckan', 'ckanapi']:
            details.append('installed from source')
        if ckan_detail or not compatible or package_key in ['ckan', 'ckanapi']:
            if not fix_versions:
                details.append('no fix version listed')
            if ckan_detail:
                details.append(ckan_detail)
            add_email_report_entry(name=name, installed_version=installed_version,
                                   reasons=details, vulnerability=vuln)
        else:
            changelog.append(f'  - {name}: {vuln_id} '
                             f'({"; ".join(details) or "no usable fix version"})')
        if not compatible:
            continue
        selected = select_fix_version(installed_version, compatible)
        if selected:
            package_fixes.append(selected)
    if not package_fixes:
        continue
    recommended_version = max(package_fixes)
    if supports_python(name, recommended_version) is not True:
        changelog.append(f'  - {name}: no verified combined '
                         f'Python {TARGET_PYTHON} recommendation')
        continue
    existing = packages.get(package_key)
    if existing is None or recommended_version > existing['version']:
        packages[package_key] = {'name': name, 'version': recommended_version,
                                 'ckan_pinned': False}
    if package_key in ckan_pins:
        ckan_name, ckan_version = ckan_pins[package_key]
        packages[package_key]['name'] = ckan_name
        packages[package_key]['version'] = ckan_version
        packages[package_key]['ckan_pinned'] = True


def split_slack_text(text, max_length=1900):
    chunks = []
    while len(text) > max_length:
        split_at = text.rfind('\n', 0, max_length)
        if split_at == -1:
            split_at = max_length
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip('\n')
    if text:
        chunks.append(text)
    return chunks


def generate_report(reports):
    blocks = [
        {
            'type': 'header',
            'text': {
                'type': 'plain_text',
                'text': 'Unsupported Python Packages :rotating_light:',
                'emoji': True,
            },
        },
        {
            'type': 'section',
            'fields': [
                {'type': 'mrkdwn', 'text': '*Project:*\nCKAN'},
                {'type': 'mrkdwn', 'text': f'*Target Python:*\n{TARGET_PYTHON}'},
            ],
        },
        {'type': 'divider'},
    ]
    fields = []
    for i, name in enumerate(sorted(reports, key=str.lower)):
        entry = reports[name]
        text = f'*{name}* (installed: `{entry["installed_version"]}`)\n\n*Reasons:*\n'
        for r in entry['reasons']:
            text += f'• {r}\n'
        text += '\n*Vulnerabilities:*\n'
        for vuln in entry['vulnerabilities']:
            fix_text = ', '.join(f'`{v}`' for v in vuln['fix_versions']) \
                if vuln['fix_versions'] else 'None listed'
            text += f'• `{vuln["id"]}` — Available fixes: {fix_text}\n'
        text = text.strip()
        if len(text) > 2000:
            if fields:
                blocks.append({
                    'type': 'section',
                    'fields': fields,
                })
                fields = []
            for chunk in split_slack_text(text):
                blocks.append({
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': chunk,
                    },
                })
        else:
            fields.append({
                'type': 'mrkdwn',
                'text': text,
            })
            if len(fields) == 2:
                blocks.append({
                    'type': 'section',
                    'fields': fields,
                })
                fields = []
        if i + 1 < len(reports):
            blocks.append({'type': 'divider'})
    if fields:
        blocks.append({
            'type': 'section',
            'fields': fields,
        })
    return {'blocks': blocks}


requirements = []
for package in sorted(packages):
    details = packages[package]
    name = details['name']
    if name in ['ckan', 'ckanapi']:
        continue  # never have ckan or ckanapi as a requirement, we install from source
    version = details['version']
    if details.get('ckan_pinned', False):
        requirements.append(f'{name}=={version}  # Pinned by CKAN requirements.txt;')
        continue
    requirements.append(f'{name}=={version}')

REQUIREMENTS_FILE.write_text(
    '# NOTE: file is managed by pip-audit workflow, '
    'see .github/workflows/pip_audit.yml\n' +
    '\n'.join(requirements) + '\n')
CHANGELOG_FILE.write_text('\n'.join(changelog) + '\n')
SLACK_FILE.write_text(json.dumps(
    generate_report(slack_reports), ensure_ascii=False, indent=2), encoding='utf-8')
