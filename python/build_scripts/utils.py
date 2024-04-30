import subprocess
import pathlib
import tempfile


class Git:
    @staticmethod
    def get_revision_hash(short=False):
        cmd = ['git', 'rev-parse', 'HEAD']
        if short:
            cmd.insert(2, '--short')
        return subprocess.check_output(cmd).decode('ASCII').strip()


class PyInstaller:

    FILE_WITH_VERSION_INFORMATION = """
# Version info from Google Chrome
# Get this info with util `pyi-grab_version`

# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
    # Set not needed items to zero 0.
    filevers=(0, 0, 0, 0),
    prodvers=(0, 0, 0, 0),
    # Contains a bitmask that specifies the valid bits 'flags'r
    mask=0x17,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to change it.
    OS=0x4,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904b0',
        [StringStruct(u'CompanyName', u'Fable Studio LLC'),
        StringStruct(u'FileVersion', u'0, 0, 0, 0'),
        StringStruct(u'InternalName', u'thistle-gulch'),
        StringStruct(u'LegalCopyright', u'Copyright 2024 Fable Studio LLC. All rights reserved.'),
        StringStruct(u'ProductName', u'NAME'),
        StringStruct(u'ProductVersion', u'VERSION')]),
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)"""

    @staticmethod
    def create_version_file(name, version, dest=None) -> pathlib.Path:
        if dest:
            # Delete existing file if it exists.
            version_file = pathlib.Path(dest)
            if version_file.exists():
                version_file.unlink()
        else:
            version_file = pathlib.Path(tempfile.gettempdir(), f"{name}_version.py")

        data = PyInstaller.FILE_WITH_VERSION_INFORMATION
        data = data.replace("u'NAME'", f"u'{name}'")
        data = data.replace("u'VERSION'", f"u'{version}'")

        # Create the version data file (windows only)
        with version_file.open("w") as f:
            f.write(data)

        return version_file
