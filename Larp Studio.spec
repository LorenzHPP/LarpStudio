# Build on Windows with the app's installed environment.
from PyInstaller.utils.hooks import collect_all
datas = [('ui', 'ui'), ('services.json', '.'), ('licenses', 'licenses'),
         ('LICENSE', '.'), ('THIRD-PARTY.md', '.'), ('README.md', '.'), ('README.de.md', '.'), ('START-HIER.txt', '.')]
binaries = []
hiddenimports = ['engine', 'transport', 'driving', 'artwork', 'route_library']
for package in ['webview', 'pymobiledevice3', 'pmd_pytcp', 'pmd_net_addr', 'pytun_pmd3']:
    package_datas, package_binaries, package_imports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_imports
a = Analysis(['app.py'], pathex=[], binaries=binaries, datas=datas,
             hiddenimports=hiddenimports, hookspath=[], hooksconfig={},
             runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Larp Studio',
          debug=False, bootloader_ignore_signals=False, strip=False,
          upx=False, console=False, icon='ui/assets/larp-studio.ico')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Larp Studio')
