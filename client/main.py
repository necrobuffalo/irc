#!/usr/bin/env python

# This is a modified/extended version of the Twisted curses client example.
# Original example copyright (c) Twisted Matrix Laboratories.

# System Imports
import curses, time, traceback, sys
import curses.wrapper

# Twisted imports
from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import LineReceiver


class TextTooLongError(Exception):
    pass


class CursesStdIO:
    """fake fd to be registered as a reader with the twisted reactor.
       Curses classes needing input should extend this"""

    def fileno(self):
        """ We want to select on FD 0 """
        return 0

    def doRead(self):
        """called when input is ready"""

    def logPrefix(self):
        return 'CursesClient'


class IRC(LineReceiver):
    """ A protocol object for IRC """

    nick = None

    def __init__(self, screenObj):
        self.screenObj = screenObj
        self.screenObj.irc = self

    def lineReceived(self, line):
        # Parse the line we received and format it appropriately
        cmd = line.strip().partition(" ")
        if cmd[0] == "PING":
            self.sendLine("PONG")
        if cmd[0] == "NICK":
            self.nick = cmd[2]
            self.screenObj.addLine("You are now known as {}".format(cmd[2]))
        elif cmd[0] == "JOIN":
            split = cmd[2].partition(" ")
            self.screenObj.addLine("{} joined {}".format(split[2], split[0]))
        elif cmd[0] == "PART":
            split = cmd[2].partition(" ")
            self.screenObj.addLine("{} left {}".format(split[2], split[0]))
        elif cmd[0] == "LIST":
            self.screenObj.addLine(
                "Channels on this server: {}".format(cmd[2]))
        elif cmd[0] == "NAMES":
            split = cmd[2].partition(" ")
            self.screenObj.addLine(
                "In channel {}: {}".format(split[0], split[2]))
        elif cmd[0] == "PRIVMSG":
            split = cmd[2].partition(" ")
            chan = split[0]
            sender = split[2].partition(" ")[0]
            received = split[2].partition(" ")[2]
            if chan == self.nick:
                self.screenObj.addLine("{} > {}".format(sender, received))
            else:
                self.screenObj.addLine(
                    "{}: {} > {}".format(chan, sender, received))
        elif cmd[0] == "ERROR":
            self.screenObj.addLine(cmd[2], 3)

    def connectionMade(self):
        self.screenObj.addLine("* CONNECTED *")

    def clientConnectionLost(self, connection, reason):
        pass


class IRCFactory(ClientFactory):
    """
    Factory used for creating IRC protocol objects
    """

    protocol = IRC

    def __init__(self, screenObj):
        self.irc = self.protocol(screenObj)

    def buildProtocol(self, addr=None):
        return self.irc

    def clientConnectionLost(self, conn, reason):
        pass


class Screen(CursesStdIO):
    def __init__(self, stdscr):
        self.timer = 0
        self.statusText = "IRC -"
        self.searchText = ''
        self.stdscr = stdscr

        # set screen attributes
        self.stdscr.nodelay(1)  # this is used to make input calls non-blocking
        curses.cbreak()
        self.stdscr.keypad(1)
        curses.curs_set(0)  # no annoying mouse cursor

        self.rows, self.cols = self.stdscr.getmaxyx()
        self.lines = []

        curses.start_color()

        # create color pairs
        # status bar
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        # normal message text
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
        # error text
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)

        self.paintStatus(self.statusText)

    def connectionLost(self, reason):
        self.close()

    def addLine(self, text, color=2):
        """ add a line to the internal list of lines"""

        self.lines.append((text, color))
        self.redisplayLines()

    def redisplayLines(self):
        """ method for redisplaying lines
            based on internal list of lines """

        self.stdscr.clear()
        self.paintStatus(self.statusText)
        i = 0
        index = len(self.lines) - 1
        while i < (self.rows - 3) and index >= 0:
            self.stdscr.addstr(self.rows - 3 - i, 0, self.lines[index][0],
                               curses.color_pair(self.lines[index][1]))
            i = i + 1
            index = index - 1
        self.stdscr.refresh()

    def paintStatus(self, text):
        if len(text) > self.cols: raise TextTooLongError
        self.stdscr.addstr(self.rows - 2, 0,
                           text + ' ' * (self.cols - len(text)),
                           curses.color_pair(1))
        # move cursor to input line
        self.stdscr.move(self.rows - 1, self.cols - 1)

    def doRead(self):
        """ Input is ready! """
        curses.noecho()
        self.timer = self.timer + 1
        c = self.stdscr.getch()  # read a character

        if c == curses.KEY_BACKSPACE:
            self.searchText = self.searchText[:-1]

        elif c == curses.KEY_ENTER or c == 10:
            self.addLine(self.searchText)
            # parse self.searchText
            self.parseCommand(self.searchText)
            self.stdscr.refresh()
            self.searchText = ''

        else:
            if len(self.searchText) == self.cols - 2: return
            try:
                self.searchText = self.searchText + chr(c)
            except ValueError:
                pass

        self.stdscr.addstr(self.rows - 1, 0, self.searchText +
                           (' ' * (self.cols - len(self.searchText) - 2)))
        self.stdscr.move(self.rows - 1, len(self.searchText))
        self.paintStatus(self.statusText + ' %d' % len(self.searchText))
        self.stdscr.refresh()

    def close(self):
        """ clean up """

        curses.nocbreak()
        self.stdscr.keypad(0)
        curses.echo()
        curses.endwin()

    def parseCommand(self, line):
        cmd = line.strip().partition(" ")

        if cmd[0] == "/msg":
            self.irc.sendLine("PRIVMSG {}".format(cmd[2]))
        elif cmd[0] == "/quit":
            self.irc.sendLine("QUIT")
            self.connectionLost()
        elif cmd[0] == "/nick":
            self.irc.sendLine("NICK {}".format(cmd[2]))
        elif cmd[0] == "/join":
            self.irc.sendLine("JOIN {}".format(cmd[2]))
        elif cmd[0] == "/part":
            self.irc.sendLine("PART {}".format(cmd[2]))
        elif cmd[0] == "/list":
            self.irc.sendLine("LIST {}".format(cmd[2]))
        elif cmd[0] == "/names":
            self.irc.sendLine("NAMES {}".format(cmd[2]))
        else:
            self.addLine("Invalid slash command.")


if __name__ == '__main__':
    stdscr = curses.initscr()  # initialize curses
    screen = Screen(stdscr)  # create Screen object
    stdscr.refresh()
    ircFactory = IRCFactory(screen)
    reactor.addReader(screen)  # add screen object as a reader to the reactor
    reactor.connectTCP("localhost", 9000, ircFactory)  # connect to IRC
    reactor.run()  # have fun!
    screen.close()
