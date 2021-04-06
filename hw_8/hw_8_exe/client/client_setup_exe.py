from cx_Freeze import setup, Executable

build_exe_options = {
    "packages": ["common", "logs", "client"],
}
setup(
    name="messenger_client",
    version="0.0.1",
    description="messenger_client",
    options={
        "build_exe": build_exe_options
    },
    executables=[Executable('client.py',
                            base='Win32GUI',
                            targetName='client.exe',
                            icon='client.ico'
                            )]
)
