# pyii-scriptbot
Python 3 IRC bot

## What it is
pyii-scriptbot is an *allegedly* simple bot which uses the IRC program **ii** to connect to IRC. It watches the FIFO pipes ii creates for changes through inotify, and runs scripts when IRC users ask it to.

License: MIT
This project benefited from MIT licensed code in the pyinotify tutorial here: https://github.com/seb-m/pyinotify

## Dependencies
* Python3.

Python 3 packages:
* pyinotify
* pexpect

External programs:
* ii

If you're on Debian/Ubuntu, run:

```
sudo apt-get install python3 python3-pip ii
sudo pip3 install pyinotify pexpect
```

## How to Use it
`python3 scriptbot.py --nick botnick --srv irc-server.net --chan #channel --port 6667`

the nick and server are mandatory; the channel defaults to #robotlounge, the port defaults to 6667.

## How to Interact with it
The preinstalled scripts are:
* list_scripts
* rng

Any IRC user can execute a script by saying the bot's name followed by a colon. The first word has to match a script, the rest of the line is sent to the script as command line arguments.

## Planned features
The 'Alias' class also has placeholders for restricting execution to when the user is authenticated with NickServ.
Additionally, there is a placeholder flag that the bot will send the output of certain scripts to the user privately, even if they announce the execution privately.

Default Flags are an attempt to validate input before it goes to the script. The RNG script included shows this style of flags: "--flag"
Users don't manually type in the flags, but rather their arguments are zippered with the given flags. The "--user" flag is always filled with the IRC nick giving the command.
There is no way to configure Default Flags for the scripts at this time, but this could done when the Aliases are created from the script listing.

When sending a private message to the bot, the header "Botnick: " is still required before the bot will execute a command. In private, maybe there is a better way to execute this?

"Hot characters" would execute certain scripts when a message starts with a single character, such as "@" or ">". The intention for these commands was that the output always be announced to the relevant channel, to facilitate an IRC RPG.

The comma separator, for messages starting with "Botnick, " is meant to activate a "query", or a natural language processing of the sentence rather than a fixed script execution. No natural language code is currently installed. I plan to connect this to some analysis of the non-command text the bot intercepts, i.e. participating conversationally.

## Warts
I haven't made progress in about a year, so I have decided to release the code in hopes someone will find it useful.

Unfortunately, the program is getting difficult to extend. The program runs as a series of threads, which pass messages to each other via queues. However, since the direction is almost entirely in a fixed sequence, the program should probably not be multithreaded. This also causes peculiarity when creating the subprocesses of the scripts.

Instead of starting from scratch once again, I've decided to make use of the code I already have, which is operational enough to pass script output to my IRC channel.
