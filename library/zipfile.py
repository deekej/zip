#!/usr/bin/python

# Copyright: (c) 2022, Dee'Kej <devel@deekej.io>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: zipfile

short_description: Archives the given paths to produce M(.zip) file.

description:
  - Primary goal of this module (when compared to M(archive) module) is to provide the possibility to specify compression level and flattening (junkining) of paths inside the archive.

options:
  paths:
    description:
      - List of paths to be (files/folders) to be archived.
    required: true
    type: list
    elements: path

  filename:
    description:
      - Filename for the resulting ZIP archive.
    required: true
    type: path

  chdir:
    description:
      - Path where to change current working directory before initiating the archival process.
      - Allows to use relative paths in the M(paths) option.
    required: false
    default: null
    type: path

  compress_level:
    description:
      - Allows overriding default compression level for the archival process.
      - Can be useful when archiving huge files to bring down the notarization time on Apple servers.
      - M(default) value corresponds to level M(-1), which default of the M(zlib) library. Currently it should equal to compression level M(6).
      - M(none) value corresponds to level M(0).
      - M(fast) value corresponds to level M(1).
      - M(best) value corresponds to level M(9).
    required: false
    default: default
    type: str
    choices:
      - default
      - none
      - fast
      - best
      - -1
      - 0
      - 1
      - 2
      - 3
      - 4
      - 5
      - 6
      - 7
      - 8
      - 9

  flatten:
    description:
      - This flag force the paths of the files being archived to be flatten (junked), meaning that only the actual filenames will be present in the archive - not full paths.
      - Corresponds to M(--junk-paths) option of M(zip) command.
  required: false
  default: false
  type: boolean

  force:
    description:
      - Force the M(filename) archive to be recreated in case it already exists.
  required: false
  default: false
  type: boolean

author:
    - Dee'Kej (@deekej)
'''

EXAMPLES = r'''
- name: Preparing the signed binaries for notarization
  zip:
    paths:
      - foo-darwin-arm64
      - bar-darwin-amd64
    filename:     "signed-binaries-v{{ version }}.zip"
    flatten:      true
    force:        true
'''

# =====================================================================

import os
import shutil
import subprocess
import zipfile

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.basic import env_fallback

COMPRESS_MAPPING = {
    'default': -1,
    'none':     0,
    'fast':     1,
    'best':     9
}

COMPRESS_CHOICES = [
    'default', 'none', 'fast', 'best',
    '-1', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9'
]

# ---------------------------------------------------------------------

def run_module():
    global COMPRESS_MAPPING, COMPRESS_CHOICES

    # Ansible Module arguments initialization:
    module_args = dict(
        paths          = dict(type='list', required=True, elements='path'),
        filename       = dict(type='path', required=True),
        chdir          = dict(type='path', required=False, default=None),
        compress_level = dict(type='str',  requured=False, default='default', choices=COMPRESS_CHOICES),
        flatten        = dict(type='bool', required=False, default=False),
        force          = dict(type='bool', required=False, default=False)
    )

    # Parsing of Ansible Module arguments:
    module = AnsibleModule(
        argument_spec       = module_args,
        supports_check_mode = False
    )

    paths          = module.params['paths']
    chdir          = module.params['chdir']
    compress_level = module.params['compress_level']
    flatten        = module.params['flatten']
    force          = module.params['force']

    filename = os.path.expanduser(module.params['filename'])

    if chdir:
        chdir = os.path.expanduser(chdir)

    result = dict(
        changed        = False,
        paths          = paths,
        filename       = filename,
        chdir          = chdir,
        compress_level = compress_level,
        flatten        = flatten,
        force          = force
    )

    # -----------------------------------------------------------------

    if chdir:
        try:
            os.chdir(chdir)
        except Exception as ex:
            module.fail_json(msg=str(ex), **result)

    if not force and os.path.exists(filename):
        module.exit_json(**result)

    archive_paths = {}

    for path in paths:
        if not os.path.exists(path):
            module.fail_json(msg="path does not exist: %s" % path, **result)
        else:
            path = os.path.expanduser(path)

            if flatten:
                archive_paths[path] = os.path.basename(path)
            else:
                # NOTE: Archive names should be relative to the archive root,
                # that is, they should not start with a path separator:
                archive_paths[path] = path.lstrip('/')

    # -----------------------------------------------------------------

    if compress_level in COMPRESS_MAPPING:
        compress_level = COMPRESS_MAPPING[compress_level]
    elif not isinstance(compress_level, int):
        module.fail_json(msg="incorrect value for 'compress_level' option: %s" % compress_level, **result)
    else:
        compress_level = int(compress_level)

    with zipfile.ZipFile(filename, mode='w', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=compress_level) as zipped_file:
        for path, archive_path in archive_paths.items():
            zipped_file.write(path, arcname=archive_path)

    result['changed'] = True

    module.exit_json(**result)

# =====================================================================

def main():
    run_module()


if __name__ == '__main__':
    main()
