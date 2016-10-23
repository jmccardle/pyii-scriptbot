import os, sys
import queue
import time
from multiprocessing import Queue

from BotThreads import *
from ReadForwardFile import ReadForwardFile
from quote_split import quote_split

import subprocess

def find_arg(flag):
    #flag is a string, usually of the format "--something"
    #this function returns quoted sections as a single argument
    args = quote_split(' '.join(sys.argv[1:]))
    if flag in args:
        return args[args.index(flag)+1]
    else:
        return None

class Alias:
    def __init__(self, whisper=False, preset_flags=None, script=None, authonly=False):
        self.whisper = whisper
        if preset_flags is None:
            self.preset_flags = []
        else:
            self.preset_flags = preset_flags
        if script is None:
            self.script = "scripts/null.sh"
        else:
            self.script = script
        self.authonly = authonly
    def __getitem__(self, arg):
        return self.__dict__[arg]


def main():
    #Parse necessary arguments from command line
    #Edit this block to set reasonable personal defaults
    irc_nick = find_arg("--nick")
    if irc_nick is None:
        print("Required argument: --nick")
        sys.exit()
    irc_srv = find_arg("--srv")
    if irc_srv is None:
        print("Requred argument: --srv")
        sys.exit()
    irc_channels = [find_arg("--chan")]
    if None in irc_channels:
        irc_channels = ['#robotlounge']
    port = find_arg('--port')
    if port is None:
        port = '6667'
    inotify_dir = os.getcwd() + '/{}/'.format(irc_srv)

    #create subdirectories for ii's server and channels
    if not os.path.exists(inotify_dir):
        os.makedirs(inotify_dir)
    for d in irc_channels:
        if not os.path.exists(inotify_dir + d):
            os.makedirs(inotify_dir + d)

    #Loads filenames into queue when files in inotify_dir are changed
    changed_files = Queue()
    watch_thread = INotifyWatchThread(inotify_dir, changed_files)
    watch_thread.daemon = True
    watch_thread.name = 'watch_thread'
    watch_thread.start()

    #starts the ii subprocess
    ii_thread = IRCClientThread(os.getcwd(), irc_srv, port, irc_nick)
    ii_thread.daemon = True
    ii_thread.name = 'ii_thread'
    ii_thread.start()

    messages = Queue()
    commands = Queue()

    #processes every individual line sent through IRC
    irc_message_thread = IRCMessageThread(messages, commands)
    irc_message_thread.daemon = True
    irc_message_thread.name = 'irc_message_thread'
    irc_message_thread.start()

    #conbobulates arguments and starts subprocesses
    aliases = {
            #"test1": Alias() #the default null alias
            }
    listscripts = subprocess.getoutput("./scripts/list_scripts")
    #print("Scripts installed: {}".format(listscripts))
    for line in listscripts.split('\n'):
        cmd = line.split('.')[0]
        aliases[cmd] = Alias(script="scripts/" + line)
    symbols = {}
    bot_scripts_thread = BotScriptsThread(commands, irc_nick, aliases, symbols)
    bot_scripts_thread.daemon = False
    bot_scripts_thread.name = 'bot_scripts_thread'
    bot_scripts_thread.start()

    #delay to allow ii to create FIFO pipes before file examiner attempts use
    time.sleep(2)

    #Opens modified files from watch_thread and queues the lines for processing by irc_message_thread
    file_examiner_thread = FileExaminerThread(changed_files, messages, inotify_dir, irc_channels)
    file_examiner_thread.daemon = False
    file_examiner_thread.name = 'file_examiner_thread'
    file_examiner_thread.start()

    threads = [watch_thread, ii_thread, irc_message_thread, bot_scripts_thread, file_examiner_thread]
    while True:
        time.sleep(2)
        for t in threads:
            if not t.is_alive():
                print("{} seems dead, as a precaution I will terminate".format(t.name))
                sys.exit()

if __name__ == '__main__':
    main()
