import subprocess
#import threading
from multiprocessing import Process
import pyinotify
import pexpect
import os
import time
import queue

from ReadForwardFile import ReadForwardFile
from quote_split import quote_split

class SubprocessThread(Process):
    def __init__(self, script, infile=None, outfile=None):
        self.script = script
        self.infile = infile
        self.outfile = outfile
        Process.__init__(self)

    def run(self):
        subprocess.check_call(self.script, stdin=self.infile, stdout=open(self.outfile, "w"))

#Thread issue: pexpect (library for subprocessing)
#   requires that only a single thread interact with a particular process.
#   So all the ii interaction will be done by this thread object.
class IRCClientThread(Process):
    def __init__(self, targetdir, hostname, port, nick):
        #self.stop = False
        self.child = pexpect.spawn('ii -i %s -s %s -p %s -n %s' % (targetdir, hostname, port, nick))
        self.targetdir = targetdir
        Process.__init__(self)
        
    def run(self):
        while True:
            time.sleep(5)
            #pass

class INotifyWatchThread(Process):
    def __init__(self, targetdir, filequeue):
        self.stop = False
        self.wm = pyinotify.WatchManager()
        self.targetdir = targetdir
        self.filequeue = filequeue
        Process.__init__(self)

    def set_stop(self):
        self.stop = True

    def check_stop(self, *args):
        return self.stop

    def run(self):
        class EventHandler(pyinotify.ProcessEvent):
            def process_IN_CLOSE_WRITE(this, event):
                #print("IN_CLOSE_WRITE event: {}".format(event.pathname))
                #Add the filename to the file queue and move on.
                self.filequeue.put(event.pathname)
                #print("Size of file queue: {}".format(self.filequeue.qsize()))


            def process_IN_CLOSE_NOWRITE(this, event):
                #print("IN_CLOSE_NOWRITE event: {}".format(event.pathname))
                #No reading action required when files are closed without being written to
                pass

            def process_IN_CREATE(this, event):
                print("IN_CREATE event: {}".format(event))
                if event.dir:
                    print("Adding {} to watchmanager.".format(event.pathname))
                    self.wm.add_watch(event.pathname, pyinotify.ALL_EVENTS)
                    #bad class linkage
                    #channel_files[event.pathname + 'out'] = ReadForwardFile(event.pathname + 'out')

            # Some other flags for future use?
            #def process_IN_DELETE(this, event):
            #def process_IN_MODIFY(this, event):
            #def process_IN_OPEN(this, event):
            #def process_IN_ACCESS(this, event):
            #def process_IN_ATTRIB(this, event):
        handler = EventHandler()
        notifier = pyinotify.Notifier(self.wm, handler)
        self.wm.add_watch(self.targetdir, pyinotify.ALL_EVENTS) # pyinotify.IN_CLOSE_WRITE)
        for d in next(os.walk(self.targetdir))[1]:
            #print("Adding {} to watchmanager.".format(self.targetdir + d))
            self.wm.add_watch(self.targetdir + d, pyinotify.ALL_EVENTS)
        notifier.loop(self.check_stop)

class IRCMessageThread(Process):
    def __init__(self, messagequeue, commandqueue, 
    join_callback=lambda *args, **kwargs: None, 
    list_callback=lambda *args, **kwargs: None,
    nickserv_callback=lambda *args, **kwargs: None):
        self.stop = False
        self.messagequeue = messagequeue
        self.commandqueue = commandqueue
        self.join_callback = join_callback
        self.list_callback = list_callback
        self.nickserv_callback = nickserv_callback
        Process.__init__(self)

    def set_stop(self):
        self.stop = True

    def check_stop(self, *args):
        return self.stop

    def dissect_message(self, sourcefile, outfile, msg):
        #all lines begin with a timestamp, eg 2015-04-04 19:39
        #a dash followed by text is a server message, eg - Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY
        #a hash sign followed by a channel name is a channel message, eg #tests
        # -!- indicates a channel message
        # angle brackets indicate a nick speaking
        year, month, day = msg[0:11].split('-')
        hour, minute = msg[11:16].split(':')
        line = msg[17:]
        #print("{}-{}-{} {}:{}   >>   {}".format(year,month,day,hour,minute,line))

        #A "response" class of some sort might be handy for dissected messages.
        #until then, here's a few fields extracted from the line(s) of text in ii's output files.
        if line[0:3] == ' - ':
            category = "MOTD"
        elif line[0:3] == '-!-':
            category = "Join" #or part? Or notice.
            nick = line[3:].split('(')[0].strip()
            print(line)
            if line[0:5] == '-!- "':
                notice_text = line[5:-2]
                notice_source = sourcefile.split('/')[-2]
                #print("Notice `{}` from {}".format(notice_text, notice_source))
                if notice_source.lower() == "nickserv":
                    subject = notice_text.split()[1]
                    status = int(notice_text.split()[2])
                    self.nickserv_callback(subject, status)
            elif '(' in line: #-!- user(~user@host) has [joined/left] ["Message or Ping Timeout"]
                realname, host = line[3:].split('(')[1].split(')')[0].split('@')
                channel = line.split(' ')[-1]
                action = line.split(' ')[-2]
                #print("{} ({} @ {}) [{}] {}".format(nick, realname, host, action, channel))
                self.join_callback(nick, realname, host, channel, action)
            elif 'mode' in line: #-!- ChanServ changed mode/#chan -> +qo user
                user = line.split(' ')[-1]
                mode = line.split(' ')[-2]
                channel = line.split('/')[1].split(' ')[0]
                print("No callback for mode change. user: {} channel: {} mode: {}".format(user, channel, mode))
                
        elif line[0] == '#':
            category = "Chan"
            channel = line.split(' ')[0]
        elif line[0] == '=':
            category = "List"
            channel = line.split(' ')[1]
            users = line.split(' ')[2:]
            #print("{} users in {}".format(len(users), channel))
            self.list_callback(channel, users)
        elif line[0] == '<':
            category = "Message"
            nick = line.split('<')[1].split('>')[0]
            text = ' '.join(line.split(' ')[1:])
            channel = sourcefile.split('/')[-2]
            #print("<{}> said \"{}\" via `{}`".format(nick, text, sourcefile))
            self.commandqueue.put((channel, nick, text, outfile,))

    def run(self):
        while (not self.check_stop()):
            try:
                sourcefile, msg = self.messagequeue.get(block=True, timeout=5)
                sourcepath = sourcefile.split('/')[0:-1]
                outfile = '/'.join(sourcepath) + '/in'
                self.dissect_message(sourcefile, outfile, msg)
            except queue.Empty:
                pass

class BotScriptsThread(Process):
    def __init__(self, commandqueue, mynick, aliases, symbols,
    chan_msg=lambda channel, text: None,
    priv_msg=lambda user, text: None,
    query_callback=lambda *args, **kwargs: None):
        self.stop = False
        self.mynick = mynick
        self.aliases = aliases
        self.symbols = symbols
        self.commandqueue = commandqueue
        self.chan_msg = chan_msg
        self.priv_msg = priv_msg
        self.query_callback = query_callback
        Process.__init__(self)
        #self.name = "BotScriptsThread-{}".format(self.name.split('-')[-1])

    def set_stop(self):
        self.stop = True

    def check_stop(self, *args):
        return self.stop

    def dissect_command(self, channel, sender, msg, outfile):
        #1. check permissions of user/channel for command
        #2. select new outfile for private message if command is marked "secret"
        #3. create SubProcessThread for the script/command/etc being referenced
        command_trigger = self.mynick.lower() + ':'
        query_trigger = self.mynick.lower() + ','

        if msg.lower().startswith(command_trigger):
            cmdstring = msg[msg.index(':')+1:].strip()
            cmd = cmdstring.split(' ')[0]
            args = quote_split(' '.join(cmdstring.split(' ')[1:]))
            #with open(outfile, "w") as f:
            #    f.write("Command `{}` with arguments `{}` received.\n".format(cmd, args))
            #TODO: join args together with quotes to allow quoted text to be a single argument

            #check cmd against permissions, change outfile if needed, and reply with the output or an error
            if cmd in self.aliases:
                if self.aliases[cmd]['whisper']:
                    outfile = '/'.join(outfile.split('/')[0:-2] + [sender, '/', 'in'])
                    print("Private command, redirecting to {}".format(outfile))
                script = self.aliases[cmd]['script']

                #args need to be zippered: flag, then arg. 
                #Not enough args: error. Not enough flags: extra args go on the end.
                if len(args) < len(self.aliases[cmd]['preset_flags']):
                    #message('', '/j {}'.format(sender))
                    with open(outfile, "w") as f:
                        f.write('Error: Flags {} required'.format(', '.join(aliases[cmd]['preset_flags'])))
                    return

                zipperedargs = []
                #All but last flag get a single argument
                for fl in self.aliases[cmd]['preset_flags'][0:-1]:
                    zipperedargs.extend([fl, args.pop(0)])
                #last flag gets all remaining arguments
                zipperedargs.extend(self.aliases[cmd]['preset_flags'][-1:] + args)
                #with open(outfile, "w") as f:
                #    f.write("Running `{}`\n".format([script] + zipperedargs))

                #TODO: if aliases[cmd].authonly: Use a global callback dictionary to await response to NICKSERV msg

                #Run the script
                print("Script output to {}".format(outfile))
                script_thread = SubprocessThread([script] + zipperedargs, None, outfile)
                script_thread.daemon = True
                script_thread.start()
            else:
                #self.priv_msg(sender, "")
                error_msg = "Command `{}` not found. Commands installed: {}\n".format(cmd, ", ".join([a for a in self.aliases.keys()]))
                with open(outfile, "w") as f:
                    f.write(error_msg)
        elif msg.lower().startswith(query_trigger):
            querystring = msg[msg.index(',')+1:].strip()
            #send query to Q&A system
            #with open(outfile, "w") as f:
            #    f.write("Query `{}` received.\n".format(querystring))
            self.query_callback(sender, channel, querystring)
        elif msg[0] in self.symbols: #config['script_hotsymbols']:
            symbol = msg[0]
            cmd = msg[1:].strip().split(' ')[0]
            args = ' '.join(msg[1:].strip().split(' ')[1:])
            #run script from the directory listed in the hotsymbol dictionary
            with open(outfile, "a") as f:
                f.write("Symbol `{}` will run `{}` in `{}`, args `{}`\n".format(
                symbol, cmd, self.symbols[symbol], args))

    def run(self):
        while (not self.check_stop()):
            try:
                channel, nick, text, outfile = self.commandqueue.get(block=True, timeout=5)
                self.dissect_command(channel, nick, text, outfile)

            except queue.Empty:
                pass
        #print("Bot script thread terminated.")

class FileExaminerThread(Process):
    def __init__(self, filequeue, messagequeue, inotify_dir, irc_channels):
        self.stop = False
        self.filequeue = filequeue
        self.messagequeue = messagequeue
        Process.__init__(self)

        self.channel_files = {}
        #Join the initial channels
        self.channel_files[inotify_dir + 'out'] = ReadForwardFile(inotify_dir + 'out')
        for channel in irc_channels:
            with open(inotify_dir + 'in', 'w') as f:
                f.write('/j {}\n'.format(channel))
                channel_out_file = inotify_dir + channel + '/out'
                self.channel_files[channel_out_file] = ReadForwardFile(channel_out_file)
        #Subfolders, including private messages
        for d in next(os.walk(inotify_dir))[1]:
            full_path = inotify_dir + d + '/out'
            if not full_path in self.channel_files:
                #print("Creating ReadForwardFile for {}".format(full_path))
                self.channel_files[full_path] = ReadForwardFile(full_path)
            else:
                #print("Disregarding {}: already initialized.".format(d))
                pass

    def set_stop(self):
        self.stop = True

    def check_stop(self, *args):
        return self.stop

    def run(self):
        while (not self.check_stop()):
            try:
                source = self.filequeue.get(block=True, timeout=5)
                #given source file, transform slighly to get our output file:
                if source.split('/')[-1] == 'out':
                    sourcepath = source.split('/')[0:-1]
                    outfile = '/'.join(sourcepath) + '/in'

                    #print("dissecting message `{}`".format(message))
                    #dissect_message(source, outfile, message)
                    if source not in self.channel_files:
                        #print("[CrashData] source: {}  sourcepath: {}".format(source, sourcepath))
                        self.channel_files[source] = ReadForwardFile(source)
                    else:
                        for line in self.channel_files[source].complete_lines():
                            self.messagequeue.put((source, line))
                
            except queue.Empty:
                pass


#if __name__ == '__main__':
#    t = SubprocessThread(['ls', '-l', '-a'], None, 'output.txt')
#    t.start()
#    t.join()
