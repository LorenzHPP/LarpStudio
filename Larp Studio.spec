# Build on Windows with the app's installed environment.
from PyInstaller.utils.hooks import collect_all, copy_metadata
datas = [('ui', 'ui'), ('services.json', '.'), ('licenses', 'licenses'),
         ('LICENSE', '.'), ('THIRD-PARTY.md', '.'), ('README.md', '.'), ('README.de.md', '.'), ('START-HERE.txt', '.'), ('START-HIER.txt', '.')]
binaries = []
hiddenimports = ['engine', 'transport', 'driving', 'artwork', 'route_library', 'storage']
# Several transitive device packages obtain their version at import time.
datas += copy_metadata('pymobiledevice3', recursive=True)
datas += copy_metadata('pywebview', recursive=True)
for package in ['webview', 'pymobiledevice3', 'pmd_pytcp', 'pmd_net_addr', 'pytun_pmd3']:
    package_datas, package_binaries, package_imports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_imports
a = Analysis(['app.py'], pathex=[], binaries=binaries, datas=datas,
             hiddenimports=hiddenimports, hookspath=[], hooksconfig={},
             runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='Larp Studio',
          debug=False, bootloader_ignore_signals=False, strip=False,
          upx=False, console=False, icon='ui/assets/larp-studio.ico')
