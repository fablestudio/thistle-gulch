# -*- mode: python ; coding: utf-8 -*-
# Allow importing from our other module.
import sys
import os
from build_scripts.utils import PyInstaller, Git  #, Pipenv
#from PyInstaller.utils.hooks import copy_metadata, collect_data_files, collect_system_data_files

sys.path.append(os.getcwd())

# CUSTOM CODE
name = "thistle-gulch"
script = "run_demos.py"
rev_hash = Git.get_revision_hash(short=True)
version = f"0.0.1-{rev_hash}"
version_file = PyInstaller.create_version_file(name, version)

# SPEC FILE

# TODO: Looks like pycrypto is dead and pycryptodome isn't supported. Recent code uses tinyaes, but no release til 4.0
# See https://github.com/pyinstaller/pyinstaller/issues/4904
# See https://github.com/pyinstaller/pyinstaller/issues/4170
# if SECRET_CIPHER:
#     block_cipher = PyiBlockCipher(key=SECRET_CIPHER)
# else:
#     block_cipher = None

block_cipher = None

datas = [("../.venv/Lib/site-packages/fable_saga/prompt_templates", "./fable_saga/prompt_templates")]
#datas += [("../secrets/fable_wizard_analytics_credentials.json", ".")]
#datas += copy_metadata("google-api-python-client")
#datas += copy_metadata("google-cloud-logging")
#datas += collect_system_data_files(".venv\Lib\site-packages\fable_saga\prompt_templates", "")
print(f"Copied {datas}")

a = Analysis(
    ["..\\" + script],
    pathex=["..\\.venv"],
    binaries=[],
    datas=datas,
    hiddenimports=["engineio.async_drivers.aiohttp", "tiktoken_ext.openai_public"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    version=version_file,
)
