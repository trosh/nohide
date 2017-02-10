#!/usr/bin/env python3

import curses

# vertical offset
VOFF = 1
HOFF = 4

class Editor():
    line = 0
    char = 0
    # TODO displine = 0
    dispchar = 0
    userchar = 0
    showHidden = False

    def updateCursor(self):
        #self.stdscr.addstr(
        #    1, 0,
        #    "line: {}, col: {}".format(
        #        self.line, self.char),
        #    curses.color_pair(2))
        #self.stdscr.addstr(
        #    2, 0,
        #    "displine: {}, dispcol: {}, usercol: {}".format(
        #        self.line, self.dispchar, self.userchar),
        #    curses.color_pair(2))
        self.stdscr.move(self.line + VOFF, self.dispchar + HOFF)

    def setChar(self, userchar):
        nc = 0
        ndispc = 0
        for v in self.vis[self.line]:
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
                line = max(0, len(self.text) - 1)
        else:
            line = 0
        self.setChar(self.userchar)

    def incChar(self):
        while True:
            self.char += 1
            if self.char == len(self.vis[self.line]) + 1:
                # EOL
                if self.line + 1 == len(self.text):
                    # EOF
                    self.char -= 1
                    break
                self.line += 1
                self.char = 0
                self.dispchar = -1
            EOL = self.char == len(self.vis[self.line])
            SHO = self.showHidden
            if not EOL:
                VIS = self.vis[self.line][self.char]
            if EOL or SHO or VIS:
                self.dispchar += 1
            if EOL or VIS:
                break
        self.userchar = self.dispchar
        self.updateCursor()

    def decChar(self):
        while True:
            self.char -= 1
            if self.char == - 1:
                if self.line == 0:
                    self.dispchar = self.char = 0
                    break
                self.line -= 1
                self.char = len(self.vis[self.line])
                if self.showHidden:
                    self.dispchar = self.char + 1
                else:
                    self.dispchar = sum(self.vis[self.line]) + 1
            EOL = self.char == len(self.vis[self.line])
            SHO = self.showHidden
            if not EOL:
                VIS = self.vis[self.line][self.char]
            if EOL or SHO or VIS:
                self.dispchar -= 1
            if EOL or VIS:
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

    def __init__(self, stdscr, text=[], vis=None, line=0, char=0):
        self.stdscr = stdscr
        # TODO modified = False
        self.text = text
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
        self.displayLine(self.line)

    def backspace(self):
        if self.dispchar == 0:
            pass
        else:
            self.decChar()
            self.vis[self.line][self.char] = False
            self.decChar()
            self.incChar()
            self.display()

    def display(self):
        self.stdscr.clear()
        self.stdscr.addstr(
            0, 0,
            "^c to quit, ^H to toggle hidden content, arrows to move",
            curses.color_pair(2))
        for ln, line in enumerate(self.text):
            vcn = 0
            self.stdscr.addstr(
                ln + VOFF, 0,
                "{:3d}".format(ln))
            for cn, c in enumerate(line):
                if self.vis[ln][cn]:
                    self.stdscr.addch(ln + VOFF, vcn + HOFF, c)
                    vcn += 1
                elif self.showHidden:
                    self.stdscr.addstr(
                        ln + VOFF, vcn + HOFF,
                        c, curses.color_pair(1))
                    vcn += 1
        self.updateCursor()

    def displayLine(self, ln):
        vcn = 0
        self.stdscr.move(ln + VOFF, 0)
        self.stdscr.clrtoeol()
        self.stdscr.addstr(ln + VOFF, 0, "{:3d}".format(ln))
        for cn, c in enumerate(self.text[ln]):
            if self.vis[ln][cn]:
                self.stdscr.addch(ln + VOFF, vcn + HOFF, c)
                vcn += 1
            elif self.showHidden:
                self.stdscr.addstr(
                    ln + VOFF, vcn + HOFF,
                    c, curses.color_pair(1))
                vcn += 1
        self.updateCursor()


def main(stdscr):
    stdscr.clear()
    curses.init_pair(1, curses.COLOR_RED,   curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    e = Editor(stdscr, ["hello","","world"])
    e.vis[0][-1] = False
    e.display()
    stdscr.refresh()
    while True:
        try:
            c = stdscr.getch()
            #stdscr.addstr(0, 20, "[{}]".format(c))
            if c == 263: # ^H
                e.toggleHidden()
                stdscr.clear()
                e.display()
            elif c == curses.KEY_RIGHT: e.incChar()
            elif c == curses.KEY_LEFT:  e.decChar()
            elif c == curses.KEY_UP:    e.setLine(e.line - 1)
            elif c == curses.KEY_DOWN:  e.setLine(e.line + 1)
            elif c in [127, curses.KEY_BACKSPACE]:
                e.backspace()
            else:
                e.type(chr(c))
            stdscr.refresh()
        except KeyboardInterrupt:
            break

curses.wrapper(main)
