from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor

import string


class IRC(LineReceiver):
    def __init__(self, addr, clients, channels):
        self.addr = addr
        self.clients = clients
        self.channels = channels
        self.nick = None

    def connectionLost(self, reason):
        if self.nick in self.clients:
            del self.clients[self.nick]
        for chan in self.channels.itervalues():
            chan.discard(self)
        print("Disconnected from {}".format(self.addr))

    def lineReceived(self, line):
        cmd = line.strip().partition(" ")

        if cmd[0] == "PING":
            self.handle_PING(cmd[2])
        elif cmd[0] == "NICK":
            self.handle_NICK(cmd[2])
        elif cmd[0] == "QUIT":
            self.handle_QUIT(cmd[2])
        elif self.nick == None:
            self.error("Please set a nick first.")
        elif cmd[0] == "JOIN":
            self.handle_JOIN(cmd[2])
        elif cmd[0] == "PART":
            self.handle_PART(cmd[2])
        elif cmd[0] == "LIST":
            self.handle_LIST(cmd[2])
        elif cmd[0] == "NAMES":
            self.handle_NAMES(cmd[2])
        elif cmd[0] == "PRIVMSG":
            self.handle_PRIVMSG(cmd[2])
        else:
            self.error(line)

    # Command handling functions
    def handle_NICK(self, line):
        if line.find("#") == 0:
            self.error("# reserved for channel names")
            return

        nick = line.partition(" ")[0]

        if nick in self.clients:
            self.error("Nick in use")
            return

        # Remove old nick
        if self.nick in self.clients:
            del self.clients[self.nick]
        # Record new nick
        self.nick = nick
        self.clients[nick] = self
        self.sendLine("NICK {}".format(self.nick))

    def handle_JOIN(self, line):
        for chan in line.split(","):
            if line.find("#") != 0:
                self.error("Invalid channel name: {}".format(chan))
                return

        for chan in line.split(","):
            if chan not in self.channels:
                self.channels[chan] = set()

            self.channels[chan].add(self)
            for client in self.channels[chan]:
                client.sendLine("JOIN {} {}".format(chan, self.nick))

    def handle_PART(self, line):
        for chan in line.split(","):
            if line.find("#") != 0:
                self.error("Invalid channel name: {}".format(chan))
                return

        for chan in line.split(","):
            if chan in self.channels:
                for client in self.channels[chan]:
                    client.sendLine("PART {} {}".format(chan, self.nick))

                self.channels[chan].discard(self)
            else:
                self.error("You are not in {}".format(chan))

    def handle_LIST(self, line):
        self.sendLine("LIST {}".format(string.join(self.channels.keys(), ",")))

    def handle_NAMES(self, line):
        for chan in line.split(","):
            if line.find("#") != 0:
                self.error("Invalid channel name: {}".format(chan))
                return

        for chan in line.split(","):
            if chan in self.channels:
                names = ""
                for client in self.channels[chan]:
                    names = names + client.nick + ","
                self.sendLine("NAMES {} {}".format(chan, names))

    def handle_PRIVMSG(self, line):
        split = line.partition(" ")
        for chan in split[0].split(","):
            # send message to that channel
            if chan.find("#") == 0:
                if chan not in self.channels:
                    self.error("You are not in that channel.")
                    continue
                for client in self.channels[chan]:
                    client.sendLine(
                        "PRIVMSG {} {} {}".format(chan, self.nick, split[2]))
            else:
                if chan in self.clients:
                    self.clients[chan].sendLine(
                        "PRIVMSG {} {} {}".format(chan, self.nick, split[2]))
                else:
                    self.error("That user is not on this server.")

    def handle_PING(self, line):
        self.sendLine("PONG")

    def handle_QUIT(self, line):
        self.transport.loseConnection()

    def error(self, line):
        self.sendLine("ERROR {}".format(line))


class IRCFactory(Factory):
    def __init__(self):
        self.clients = {}
        self.channels = {}

    def buildProtocol(self, addr):
        print("Connected to {}".format(addr))
        return IRC(addr, self.clients, self.channels)


reactor.listenTCP(9000, IRCFactory())
reactor.run()
