from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor


class IRC(LineReceiver):
    def __init__(self, clients):
        self.clients = clients
        self.nick = None

    def connectionLost(self, reason):
        if self.nick in self.clients:
            del self.clients[self.nick]

    def lineReceived(self, line):
        cmd = line.strip().partition(" ")

        if cmd[0] == "NICK":
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
        # TODO send some kind of properly formatted success message
        self.sendLine("You are now known as {}".format(self.nick))

    def handle_JOIN(self, line):
        pass

    def handle_PART(self, line):
        pass

    def handle_LIST(self, line):
        pass

    def handle_NAMES(self, line):
        pass

    def handle_PRIVMSG(self, line):
        pass

    def handle_QUIT(self, line):
        if self.nick in self.clients:
            del self.clients[self.nick]
        self.transport.loseConnection()

    def error(self, line):
        self.sendLine("ERROR {}".format(line))


class IRCFactory(Factory):
    def __init__(self):
        self.clients = {}

    def buildProtocol(self, addr):
        return IRC(self.clients)


reactor.listenTCP(9000, IRCFactory())
reactor.run()
