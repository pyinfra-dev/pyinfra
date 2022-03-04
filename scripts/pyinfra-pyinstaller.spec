from os import environ

from PyInstaller.utils.hooks import collect_all


ONE_FILE_MODE = environ.get('PYINFRA_BUILD_ONEDIR') != 'true'


_, binaries, hidden_imports = collect_all('pyinfra')


a = Analysis(  # noqa
    ['pyinfra-pyinstaller-entrypoint.py'],
    pathex=[],
    binaries=binaries,
    datas=[],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

a.datas = [
    data for data in a.datas
    if '.dist-info' not in data[0] and '.egg-info' not in data[0]
]

pyz = PYZ(  # noqa
    a.pure,
    a.zipped_data,
    cipher=None,
)

if ONE_FILE_MODE:
    exe = EXE(  # noqa
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='pyinfra',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=True,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )

# One directory mode (debugging)
else:
    exe = EXE(  # noqa
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='pyinfra-onedir',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=True,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )

    coll = COLLECT(  # noqa
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='pyinfra-onedir',
    )
