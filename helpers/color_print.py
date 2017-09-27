
class ColorPrint(object):
    RED = '\033[31m'
    GREEN = '\033[32m'
    ORANGE = '\033[33m'
    BLUE = '\033[34m'
    PURPLE = '\033[35m'
    CYAN = '\033[36m'
    LIGHTGREY = '\033[37m'
    DARKGREY = '\033[90m'
    LIGHTRED = '\033[91m'
    LIGHTGREEN = '\033[92m'
    YELLOW = '\033[93m'
    LIGHTBLUE = '\033[94m'
    PINK = '\033[95m'
    LIGHTCYAN = '\033[96m'
    ENDC = '\033[0m'

    def green(self, text):
        print(str.format('{}{}{}', self.GREEN, text, self.ENDC))

    def blue(self, text):
        print(str.format('{}{}{}', self.BLUE, text, self.ENDC))

    def red(self, text):
        print(str.format('{}{}{}', self.RED, text, self.ENDC))

    def purple(self, text):
        print(str.format('{}{}{}', self.PURPLE, text, self.ENDC))

    def yellow(self, text):
        print(str.format('{}{}{}', self.YELLOW, text, self.ENDC))

    def cyan(self, text):
        print(str.format('{}{}{}', self.CYAN, text, self.ENDC))

    def orange(self, text):
        print(str.format('{}{}{}', self.ORANGE, text, self.ENDC))
