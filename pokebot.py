import atexit
import platform
import sys
import json

from modules.runtime import is_bundled_app, get_base_path
from modules.version import pokebot_name, pokebot_version

recommended_python_version = "3.12"
supported_python_versions = [(3, 10), (3, 11), (3, 12)]

libmgba_tag = "0.2.0-2"
libmgba_ver = "0.2.0"

required_modules = [
    "numpy~=1.26.1",
    "Flask~=2.3.2",
    "Flask-Cors~=4.0.0",
    "ruamel.yaml~=0.18.2",
    "pypresence~=4.3.0",
    "obsws-python~=1.6.0",
    "pandas~=2.1.1",
    "discord-webhook~=1.2.1",
    "jsonschema~=4.17.3",
    "rich~=13.5.2",
    "cffi~=1.16.0",
    "Pillow~=10.0.1",
    "sounddevice~=0.4.6",
    "requests~=2.31.0",
    "pyperclip~=1.8.2",
]

if platform.system() == "Windows":
    required_modules.extend([
        "pywin32>=306",
        "psutil~=5.9.5"
    ])

gui = None


# On Windows, the bot can be started by clicking this Python file. In that case, the terminal
# window is only open for as long as the bot runs, which would make it impossible to see error
# messages during a crash.
# For those cases, we register an `atexit` handler that will wait for user input before closing
# the terminal window.
def on_exit() -> None:
    if platform.system() == "Windows":
        import psutil
        import os

        parent_process_name = psutil.Process(os.getppid()).name()
        if parent_process_name == "py.exe" or is_bundled_app():
            if gui is not None and gui.window is not None:
                gui.window.withdraw()

            print("")
            input("Press Enter to close...")


atexit.register(on_exit)


def check_requirements() -> None:
    # We do not want to do downlaod requirements every single time the bot is started.
    # As a quick sanity check, we store the current bot version in `.last-requirements-check`.
    # If that file is present and contains the current bot version, we skip the check.
    requirements_file = get_base_path() / ".last-requirements-check"
    requirements_version_hash = pokebot_version + '/' + platform.python_version()
    need_to_fetch_requirements = True
    if requirements_file.is_file():
        with open(requirements_file, "r") as file:
            if file.read() == requirements_version_hash:
                need_to_fetch_requirements = False
            else:
                print(
                    f"This is a newer version of {pokebot_name} than you have run before. "
                    f"Checking if requirements are met..."
                )
                print("")
    else:
        print(
            f"Seems like this is the first time you are running {pokebot_name}!\n"
            "Checking if requirements are met..."
        )
        print("")

    if need_to_fetch_requirements:
        print(f"The following Python modules need to be installed:\n\n{json.dumps(required_modules, indent=2)}\n\n")
        response = input("Install modules? [y/n] ")
        if response.lower() == "y":
            python_version = platform.python_version_tuple()
            version_matched = False
            for supported_version in supported_python_versions:
                if int(python_version[0]) == supported_version[0] and int(python_version[1]) == supported_version[1]:
                    version_matched = True
                    break
            if not version_matched:
                supported_versions_list = ", ".join(map(lambda t: f"{str(t[0])}.{str(t[1])}", supported_python_versions))
                print(f"ERROR: The Python version you are using (Python {platform.python_version()}) is not supported.\n")
                print(f"Supported versions are: {supported_versions_list}")
                print(f"It is recommended that you install Python {recommended_python_version}.")
                sys.exit(1)

            # Some dependencies only work with 64-bit Python. Since this isn't the 90s anymore,
            # we'll just require that.
            if platform.architecture()[0] != "64bit":
                print(f"ERROR: A 64-bit version of Python is required in order to run {pokebot_name} {pokebot_version}.\n")
                print(f"You are currently running a {platform.architecture()[0]} version.")
                sys.exit(1)

            # Run `pip install` on all required modules.
            import subprocess

            pip_flags = ["--disable-pip-version-check", "--no-python-version-warning"]
            for module in required_modules:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", *pip_flags, module],
                    stderr=sys.stderr, stdout=sys.stdout
                )

            # Make sure that `libmgba-py` is installed.
            print("")
            libmgba_directory = get_base_path() / "mgba"
            if not libmgba_directory.is_dir():
                match platform.system():
                    case "Windows":
                        libmgba_url = (
                            f"https://github.com/hanzi/libmgba-py/releases/download/{libmgba_tag}/"
                            f"libmgba-py_{libmgba_ver}_win64.zip"
                        )

                    case "Linux":
                        linux_release = platform.freedesktop_os_release()
                        supported_linux_releases = [("ubuntu", "23.04"), ("debian", "12")]
                        if (linux_release["ID"], linux_release["VERSION_ID"]) not in supported_linux_releases:
                            print(
                                f'You are running an untested version of Linux ({linux_release["PRETTY_NAME"]}). '
                                f"Currently, only {supported_linux_releases} have been tested and confirmed working."
                            )
                            input("Press enter to install libmgba-py anyway...")
                        libmgba_url = (
                            f"https://github.com/hanzi/libmgba-py/releases/download/{libmgba_tag}/"
                            f"libmgba-py_{libmgba_ver}_ubuntu-lunar.zip"
                        )

                    case _:
                        print(f"ERROR: {platform.system()} is unsupported. Only Windows and Linux are currently supported.")
                        sys.exit(1)

                import io
                import requests
                import zipfile

                response = requests.get(libmgba_url)
                if response.status_code == 200:
                    print("Unzipping libmgba into `./mgba`...")
                    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_handle:
                        zip_handle.extractall(get_base_path())

            # Mark the requirements for the current bot version as checked, so we do not
            # have to run all of this again until the next update.
            with open(requirements_file, "w") as file:
                file.write(requirements_version_hash)

        else:
            print("Exiting!")
            sys.exit(1)

    print("")


if __name__ == "__main__":
    if not is_bundled_app():
        check_requirements()

    from modules.config import load_config_from_directory
    from modules.console import console
    from modules.gui import PokebotGui, get_emulator
    from modules.main import main_loop
    from modules.profiles import profile_directory_exists, load_profile_by_name

    console.print(f"Starting [bold cyan]{pokebot_name} {pokebot_version}![/]")
    load_config_from_directory(get_base_path() / "profiles")

    # This catches the signal Windows emits when the underlying console window is closed
    # by the user. We still want to save the emulator state in that case, which would not
    # happen by default!
    if platform.system() == "Windows":
        import win32api

        def win32_signal_handler(signal_type):
            if signal_type == 2:
                emulator = get_emulator()
                if emulator is not None:
                    emulator.shutdown()

        win32api.SetConsoleCtrlHandler(win32_signal_handler, True)

    preselected_profile = None
    debug_mode = False
    for arg in sys.argv[1:]:
        if arg == "--debug":
            debug_mode = True
        elif profile_directory_exists(arg):
            preselected_profile = load_profile_by_name(arg)

    gui = PokebotGui(main_loop, on_exit)
    if debug_mode:
        from modules.gui import DebugEmulatorControls
        from modules.debug import TasksTab, BattleTab, TrainerTab, DaycareTab, SymbolsTab, InputsTab, EventFlagsTab

        controls = DebugEmulatorControls(gui, gui.window)
        controls.add_tab(TasksTab())
        controls.add_tab(BattleTab())
        controls.add_tab(TrainerTab())
        controls.add_tab(DaycareTab())
        controls.add_tab(SymbolsTab())
        controls.add_tab(EventFlagsTab())
        controls.add_tab(InputsTab())

        gui.controls = controls

    gui.run(preselected_profile)
