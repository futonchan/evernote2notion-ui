import subprocess
import os
import shutil
import sys
import importlib.util
import tkinter as tk
from tkinter import ttk
from threading import Thread
from threading import active_count
import glob
import configparser

python = sys.executable

def run(command, desc=None, errdesc=None, custom_env=None):
    if desc is not None:
        print(desc)

    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=os.environ if custom_env is None else custom_env)

    if result.returncode != 0:

        message = f"""{errdesc or 'Error running command'}.
        Command: {command}
        Error code: {result.returncode}
        stdout: {result.stdout.decode(encoding="utf8", errors="ignore") if len(result.stdout)>0 else '<empty>'}
        stderr: {result.stderr.decode(encoding="utf8", errors="ignore") if len(result.stderr)>0 else '<empty>'}
        """
        raise RuntimeError(message)

    return result.stdout.decode(encoding="utf8", errors="ignore")

def realtime_run(command_list):
    proc = subprocess.Popen(command_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True) # stdout, stderrを同じパイプにする
    while True:
        stdout_stderr_line = proc.stdout.readline()
        if stdout_stderr_line:
            yield stdout_stderr_line.decode("utf8", errors="ignore")
        if not stdout_stderr_line and proc.poll() is not None:
            break

def is_installed(package):
    try:
        spec = importlib.util.find_spec(package)
    except ModuleNotFoundError:
        return False

    return spec is not None

# def is_installed_pipx(package):

def prepare_environment():
    pipx_command = os.environ.get('PIPX_COMMAND', "pip install pipx")
    ensurepath_command = os.environ.get('ENSUREPATH_COMMAND', "pipx ensurepath")
    enex2notion_command = os.environ.get('PIPX_COMMAND', "pipx install enex2notion")
    evernote_backup_command = os.environ.get('PIPX_COMMAND', "pipx install evernote-backup")

    if not is_installed("pipx"):
        run(f'"{python}" -m {pipx_command}', "Installing pipx", "Couldn't install pipx")
    run(f'"{python}" -m {ensurepath_command}', "Setting ensurepath", "Couldn't setting ensurepath")
    run(f'"{python}" -m {enex2notion_command}', "Installing enex2notion", "Couldn't install enex2notion")
    run(f'"{python}" -m {evernote_backup_command}', "Installing evernote_backup", "Couldn't install evernote_backup")

def single_evernote2notion(email,passwd,token,config):
    if active_count() == 1:
        thread = Thread(target=evernote2notion, args=(email, passwd, token,config))
        thread.start()
    else:
        pass

def write_log(log_path, line):
    if os.path.exists(log_path):
        mode = "a"
    else:
        mode = "w"
    with open(log_path, mode, encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")

def evernote2notion(email, passwd, token, config):
    config.update("email", email)
    config.update("token", token)

    output_dir = "output/"

    init_command = f"evernote-backup init-db --user {email} --password {passwd}"
    sync_command = "evernote-backup sync"
    export_command = f"evernote-backup export {output_dir}"


    if email and passwd:
        if os.path.exists("en_backup.db"):
            os.remove("en_backup.db")
        run(f'{init_command}', "Initialize Evernote-backup", "Couldn't initialize Evernote-backup")

        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        run(f'{sync_command}', "syncing Evernote-backup", "Couldn't sync Evernote-backup")

        run(f'{export_command}', "exporting Evernote-backup", "Couldn't export Evernote-backup")
        enex_files = glob.glob(os.path.join(output_dir.replace("/", ""), "*"))
        log_path = "enex2notion.log"
        if os.path.exists(log_path):
            os.remove(log_path)
        enex2notion_command_list = ["enex2notion --verbose" + " " + f + " " + "--token" + " " + token for f in enex_files]
        for index, batch_command in enumerate(enex2notion_command_list):
            print(batch_command)
            for line in realtime_run(batch_command):
                write_log(log_path, line)
        write_log(log_path, "Finish")
        print("Finish")

    else:
        if not email:
            print("Email is empty.")
        if not passwd:
            print("Password is empty.")
        print("Try again.")

class Configure:
    def __init__(self, config, path):
        self.path = path
        if not os.path.exists(path):
            with open(path, "w") as f:
                f.write('[default]')
        config.read(path)
        self.conf = config

    def update(self, option, param):
        self.conf["default"][option] = param
        with open(self.path, "w") as f:
            self.conf.write(f)

def tkinter_main():
    root = tk.Tk()
    root.title("Evernote2Notion")

    config_path = "config.ini"
    config = Configure(configparser.ConfigParser(), config_path)

    # Email
    email_frame = tk.Frame(root)
    email_label = ttk.Label(email_frame, text="Evernote Email: ")
    email_entry = ttk.Entry(email_frame, width=100)
    if config.conf.has_option("default", "email"):
        email_entry.insert(0, config.conf["default"]["email"])
    ## Pack
    email_frame.pack()
    email_label.pack(side="left")
    email_entry.pack(side="left")

    # Passwd
    passwd_frame = tk.Frame(root)
    passwd_label = ttk.Label(passwd_frame, text="Evernote Password: ")
    passwd_entry = ttk.Entry(passwd_frame, show='*', width=100)
    ## Pack
    passwd_frame.pack()
    passwd_label.pack(side="left")
    passwd_entry.pack(side="left")

    # Token
    token_frame = tk.Frame(root)
    token_label = ttk.Label(token_frame, text="Notion token: ")
    token_entry = ttk.Entry(token_frame, show='*', width=100)
    if config.conf.has_option("default", "token"):
        token_entry.insert(0, config.conf["default"]["token"])
    ## Pack
    token_frame.pack()
    token_label.pack(side="left")
    token_entry.pack(side="left")

    # Execute Button
    execute_button = ttk.Button(root, text="GO", command=lambda:single_evernote2notion(email_entry.get(), passwd_entry.get(), token_entry.get(), config))
    execute_button.pack()

    root.mainloop()

if __name__ == "__main__":
    prepare_environment()
    tkinter_main()
