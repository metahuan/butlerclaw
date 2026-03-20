# -*- mode: python ; coding: utf-8 -*-

# Butlerclaw 龙虾管家 - PyInstaller 打包配置
# 产品级打包配置，确保在所有用户环境下正常工作

import os

a = Analysis(
    ['openclaw_assistant.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 包含技能数据文件（如果有的话）
        # (os.path.join(project_root, 'data'), 'data'),
    ],
    hiddenimports=[
        # UI/skills (imported dynamically in some places)
        'skills_panel_new',
        'skills_manager',
        # Tkinter modules used directly
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        # Security center modules. Imported in diagnostics suite; ensure PyInstaller bundles them.
        'security',
        'security.models',
        'security.permission_scanner',
        'security.skill_scanner',
        'security.vuln_patcher',
        'security.vulnerability_db',
        'security.hardening_engine',
        'security.key_rotation',
        'security.alert_manager',
        'security.vuln_monitor',
        'security.scoring_system',
        'security.compliance_checker',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不必要的模块，减小体积
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'scipy',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Butlerclaw龙虾管家',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # 添加图标（如果有的话）
    # icon=os.path.join(project_root, 'icon.ico'),
)
