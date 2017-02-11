#!/usr/bin/env python3

import curses

# vertical offset
VOFF = 2
HOFF = 0

def cvToChar(cv):
    # cv = [char, vis]
    if cv[1]:
        return cv[0]
    return ""

class Editor():
    line = 0
    char = 0
    displine = 0
    dispchar = 0
    userchar = 0
    showHidden = False
    filename = False
    cutbuffer = []
    cutting = 0

    def updateCursor(self):
        wh, ww = self.stdscr.getmaxyx()
        if self.line + VOFF >= wh:
            # TODO whaat
            return
        if self.dispchar + HOFF >= ww:
            # TODO whhaat
            return
        self.stdscr.move(self.line + VOFF, self.dispchar + HOFF)

    def setChar(self, userchar):
        ndispc = nc = 0
        for v in self.vis[self.line][:-1]:
            if v and nc >= userchar:
                break
            if self.showHidden or v:
                ndispc += 1
            nc += 1
        self.char = nc
        if ndispc == userchar:
            self.userchar = userchar
        self.dispchar = ndispc
        self.updateCursor()

    def setLine(self, line):
        if 0 <= line:
            if  line < len(self.text):
                self.line = line
            else:
                self.line = max(0, len(self.text) - 1)
                self.userchar = len(self.text[self.line]) - 1
        else:
            self.line = 0
            self.userchar = 0
        self.setChar(self.userchar)

    def incChar(self):
        while True:
            self.char += 1
            if self.char == len(self.vis[self.line]):
                # EOL
                if self.line + 1 == len(self.text):
                    # EOF
                    self.char -= 1
                    break
                self.line += 1
                self.char = 0
                self.dispchar = -1
            VIS = self.vis[self.line][self.char]
            if VIS or self.showHidden:
                self.dispchar += 1
            if VIS:
                break
        self.userchar = self.dispchar
        self.updateCursor()

    def decChar(self):
        while True:
            self.char -= 1
            if self.char == - 1:
                if self.line == 0:
                    self.dispchar = -1
                    self.incChar()
                    break
                self.line -= 1
                self.char = len(self.vis[self.line]) - 1
                if self.showHidden:
                    self.dispchar = self.char + 1
                else:
                    self.dispchar = sum(self.vis[self.line])
            VIS = self.vis[self.line][self.char]
            if VIS or self.showHidden:
                self.dispchar -= 1
            if VIS:
                break
        self.userchar = self.dispchar
        self.updateCursor()

    def hide(self):
        self.showHidden = False
        self.dispchar = 0
        for nc, v in enumerate(self.vis[self.line]):
            if v:
                if nc >= self.char:
                    break
                self.dispchar += 1
        self.userchar = self.dispchar

    def reveal(self):
        self.showHidden = True
        self.userchar = self.dispchar = self.char

    def toggleHidden(self):
        if self.showHidden:
            self.hide()
        else:
            self.reveal()

    def __init__(self, stdscr, text=["\n"], vis=None, line=0, char=0):
        self.stdscr = stdscr
        # TODO modified = False
        self.text = text
        # TODO check newlines
        self.vis = vis or [[True for c in line] for line in text]
        self.setLine(line)
        self.setChar(char)

    def type(self, c):
        self.text[self.line] = "{}{}{}".format(
            self.text[self.line][:self.char], c,
            self.text[self.line][self.char:])
        self.vis[self.line].insert(self.char, True)
        self.char += 1
        self.dispchar += 1
        self.userchar = self.dispchar
        self.displayLine()

    def newline(self):
        ln = self.line
        text = self.text[ln]
        vis = self.vis[ln]
        ch = self.char
        self.text[ln:ln+1] = [text[:ch] + "\n", text[ch:]]
        self.vis[ln:ln+1] = [vis[:ch] + [True], vis[ch:]]
        self.line += 1
        self.userchar = self.dispchar = self.char = 0
        self.display()

    def backspace(self):
        if sum(self.vis[self.line][:self.char]) == 0:
            if self.line == 0:
                return
            self.decChar()
            self.vis[self.line][self.char] = False
            if sum(self.vis[self.line][:self.char]) < 1:
                self.dispchar = self.char = -1
            else:
                self.decChar()
            self.text[self.line] += self.text[self.line+1]
            del self.text[self.line+1]
            self.vis[self.line] += self.vis[self.line+1]
            del self.vis[self.line+1]
            self.incChar()
            self.display()
        elif sum(self.vis[self.line][:self.char]) == 1:
            self.decChar()
            self.vis[self.line][self.char] = False
            self.dispchar = self.char = -1
            self.incChar()
            self.displayLine()
        else:
            self.decChar()
            self.vis[self.line][self.char] = False
            self.decChar()
            self.incChar()
            self.displayLine()

    def getVisible(self, ln):
        return "".join(map(cvToChar, zip(self.text[ln], self.vis[ln])))

    def cut(self):
        if self.cutting == 1:
            self.cutbuffer.append(self.getVisible(self.line))
            if len(self.vis) == 1 and sum(self.vis[0]) == 1:
                self.cutting = 2
        else:
            self.cutbuffer = [self.getVisible(self.line)]
            self.cutting = 1
        self.vis[self.line] = [False for n in self.text[self.line]]
        if self.line + 1 < len(self.text):
            self.text[self.line] += self.text[self.line+1]
            del self.text[self.line+1]
            self.vis[self.line] += self.vis[self.line+1]
            del self.vis[self.line+1]
            self.char = len(self.text[self.line]) - 1
            if self.showHidden:
                self.dispchar = self.char
            else:
                self.dispchar = 0
            self.incChar()
        else:
            self.vis[self.line][-1] = True
            if self.line > 0:
                self.text[self.line-1] += self.text[self.line]
                del self.text[self.line]
                self.vis[self.line-1][-1] = False
                self.vis[self.line-1] += self.vis[self.line]
                del self.vis[self.line]
                self.line -= 1
            self.char = len(self.text[self.line]) - 1
            if self.showHidden:
                self.dispchar = self.char
            else:
                self.dispchar = sum(self.vis[self.line]) - 1
        self.display()

    def uncut(self):
        self.text[self.line:self.line] = self.cutbuffer
        self.vis[self.line:self.line] = \
            [[True for c in line] for line in self.cutbuffer]
        self.line += len(self.cutbuffer)
        self.userchar = self.dispchar = self.char = 0
        self.display()

    def displayline(self, ln):
        wh, ww = self.stdscr.getmaxyx()
        #self.stdscr.addstr(ln + VOFF, 0, "{:3d}".format(ln))
        vcn = 0
        for cn, c in enumerate(self.text[ln][:-1]):
            if vcn + HOFF == ww:
                break
            if self.vis[ln][cn]:
                self.stdscr.addch(ln + VOFF, vcn + HOFF, c)
                vcn += 1
            elif self.showHidden:
                if c == "\n":
                    c = "↵"
                self.stdscr.addch(
                    ln + VOFF, vcn + HOFF,
                    c, curses.A_DIM)
                vcn += 1

    def display(self):
        self.stdscr.clear()
        self.stdscr.addstr(
            0, 0, "  NoHide nano", curses.A_REVERSE)
        self.stdscr.chgat(curses.A_REVERSE)
        wh, ww = self.stdscr.getmaxyx()
        for n in range(0, len(commands), 2):
            if (n+1)*10 > ww:
                break
            c = commands[n].split(" ", 1)
            self.stdscr.addstr(wh-2, n*10, c[0], curses.A_REVERSE)
            self.stdscr.addstr(" " + c[1])
            if n + 1 == len(commands):
                break
            c = commands[n+1].split(" ", 1)
            self.stdscr.addstr(wh-1, n*10, c[0], curses.A_REVERSE)
            self.stdscr.addstr(" " + c[1])
        for ln in range(len(self.text)):
            self.displayline(ln)
        self.updateCursor()

    def displayLine(self):
        self.stdscr.move(self.line + VOFF, 0)
        self.stdscr.clrtoeol()
        self.displayline(self.line)
        self.updateCursor()

    def write(self):
        if not self.filename:
            self.stdscr.attron(curses.A_REVERSE)
            self.stdscr.addstr(20, 0, "File Name to Write ")
            if self.showHidden:
                self.stdscr.addstr("(with hidden content) : ")
            else:
                self.stdscr.addstr("(without hidden content) : ")
            curses.echo()
            self.filename = self.stdscr.getstr()
            curses.noecho()
            self.stdscr.attroff(curses.A_REVERSE)
        with open(self.filename, "w") as f:
            if self.showHidden:
                for n, line in enumerate(self.text):
                    f.write(line)
                    f.write("".join([str(v+0) for v in self.vis[n]])+"\n")
            else:
                for n in range(len(self.text)):
                    f.write(self.visible(n))
        self.display()

commands = [
    " Exit",
    " Write Out",
    " Toggle Hidden",
    " Toggle Debug",
    " Cut Text",
    " Uncut Text"
]

def main(stdscr):
    stdscr.clear()
    e = Editor(stdscr, ["\n"])
    debug = False
    e.display()
    stdscr.refresh()
    while True:
        try:
            c = stdscr.getkey()
            if c not in ["", "KEY_RESIZE"]:
                e.cutting = 0
            if c == "KEY_RESIZE":
                e.display()
            elif c == "":
                e.toggleHidden()
                stdscr.clear()
                e.display()
            elif c == "":
                debug = not debug
                stdscr.addstr(0, 20, "[{}]".format(c))
                e.display()
            elif c == "^O":
                e.write()
            elif c == "":
                e.cut()
            elif c == "":
                stdscr.addstr(1, 40, "^U")
                e.uncut()
            elif c == "KEY_RIGHT": e.incChar()
            elif c == "KEY_LEFT":  e.decChar()
            elif c == "KEY_UP":    e.setLine(e.line - 1)
            elif c == "KEY_DOWN":  e.setLine(e.line + 1)
            elif c == "":
                e.backspace()
            elif c == "\n":
                e.newline()
            elif len(c) == 1:
                e.type(c)
            if debug:
                stdscr.addstr(0, 20, "[{}]".format(c))
                stdscr.clrtoeol()
                stdscr.chgat(curses.A_REVERSE)
                stdscr.addstr(0, 35, "c{},d{},u{}".format(
                        e.char, e.dispchar, e.userchar))
                stdscr.clrtoeol()
                stdscr.chgat(curses.A_REVERSE)
                e.updateCursor()
            stdscr.refresh()
        except KeyboardInterrupt:
            break

curses.wrapper(main)
