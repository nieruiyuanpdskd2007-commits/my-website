# PyInstaller specification for the Windows desktop application.
from pathlib import Path


root = Path(SPECPATH)

a = Analysis(
    [str(root / "desktop_main.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / "data" / "cards.json"), "data"),
        (str(root / "data" / "decks" / "mage.json"), "data/decks"),
        (str(root / "data" / "decks" / "warrior.json"), "data/decks"),
        (str(root / "data" / "standard_sets.json"), "data"),
        (
            str(root / "data" / "knowledge" / "cards.collectible.zhCN.json.gz"),
            "data/knowledge",
        ),
        (str(root / "data" / "knowledge" / "manifest.json"), "data/knowledge"),
        (str(root / "data" / "knowledge" / "coverage.json"), "data/knowledge"),
    ],
    hiddenimports=["tkinter", "tkinter.ttk", "tkinter.filedialog", "tkinter.messagebox"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="HearthstoneStandardAgent",
    console=False,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
)
