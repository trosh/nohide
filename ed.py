import sys
import re

help = """
NOHIDE (ed mode) : a line editor which doesn't really delete

                go to     next line (and print it)
    .           go to  current line (and print it)
    <int>       go to absolute line (and print it)
    <+-int>     go to relative line (and print it)
    <range>     go to end of range (and print range)
    p           print range
    P           print range, show hidden content
    n           enumerate range
    N           enumerate range, show hidden content
    i           insert before range (or current line)
    a           append after range (or current line)
    d           delete (but not really) range (or current line)
    c           change
    /<regex>    go to first match (search forward)
    g/re/<op>   apply op to all matching lines
    q           soft quit (twice to override)
    Q           hard quit

Most commands can be prefixed with a range.
For example:

    3           go to 3rd line
    +2          go down 2 lines
    g/re/p      print matching lines
    ,p          print text
    ,+0n        enumerate previous text
    .,N         enumerate from here to EOF with hidden content
    1i          prepend file
    ,a          append file
    2,-1d       delete from 2nd line to previous line
    s/old/new   substitute in line

To do:

    ?<regex>    go to first match (search backward)
    j           join range to single line (+ yank range)
    k<lc>       create mark (lowercase character)
    <arrows>    move inside line (maybe not), go through history
    w <fn>      write to file
    e <fn>      edit file (soft quit current buffer)
    G/re        ask for op, at every matching line
    v/re        apply op to all non-matching lines
    V/re        ask for op, at every non-matching line
    t<line>     copy range after line (can be 0)
    c,d,s       (+ yank range)
    y           yank range (to cut buffer)
    x           put cut buffer after line
"""


def isDigit(c):
    return "0" <= c <= "9"

def getText():
    text = []
    for line in sys.stdin:
        line = line[:-1]
        if line == ".":
            return text
        else:
            text.append([line])

def sub(s, rng):
    if len(s) == 0:
        return []
    # make iterator instead
    return s[rng[0]:rng[-1]+1]

def nsub(s, rng):
    if len(s) == 0:
        return []
    # make iterator instead
    return [(n+rng[0], s[i]) for n, i in enumerate(range(rng[0], rng[-1]+1))]

def visible(line):
    vis = ""
    for part in line:
        if type(part) == type(""):
            vis += part
    return vis

st = "\033[9m"

def complete(line):
    s = ""
    if type(line[0]) == type([]) and \
       line[0][0][-1] == "\n":
        s = "{}{}\033[m".format(st, "".join(line[0]))
        line = line[1:]
    for part in line:
        if type(part) == type(""):
            s += part
        else:
            s += "{}{}\033[m".format(st, "".join(part))
    return s

def merge(line):
    """merge hidden and visible parts of line array to string
    expects an array without initial hidden complete lines"""
    s = ""
    for part in line:
        if type(part) == type(""):
            s += part
        else:
            s += "".join(part)
    return s


class EdError(Exception):
    def __init__(self, message):
        super(EdError, self).__init__(message)
        self.msg = message

def error(s):
    raise EdError(s)


class editor:
    """an editor which doesn't really delete"""
    text = [] # Main body (visible and hidden text)
    appendix = [] # Hidden text after main body
    cursor = 0
    modified = False # To check whether to interrupt "q"
    override = False # For two consecutive "q"s (TODO consecutive "^D"s too)
    marks = False # For batch inserts with glob (TODO k command ?)
    newText = False # For batch inserts with glob

    def __init__(self, strikethrough):
        if strikethrough:
            global st
            st = strikethrough

    def getNumber(self, comm):
        """Determine number at comm start, and where it stops or -1"""
        for n, c in enumerate(comm):
            if not isDigit(c):
                return int(comm[:n])-1, n
        return int(comm)-1, -1

    def getRelative(self, comm):
        """determine relative offset at comm start, and where it stops or -1"""
        rel = 0
        sign = 0
        offset = 0
        for n, c in enumerate(comm):
            if c == "-":
                if n + 1 < len(comm) and isDigit(comm[n+1]):
                    sign = -1
                    offset = 0
                else:
                    rel -= 1
            elif c == "+":
                if n + 1 < len(comm) and isDigit(comm[n+1]):
                    sign = 1
                    offset = 0
                else:
                    rel += 1
            elif isDigit(c):
                offset = offset*10 + ord(c) - ord("0")
            else:
                end = n
                break
        else:
            end = -1
        rel += sign * offset
        return rel, end

    def search(self, comm):
        if len(comm) == 1:
            # repeat previous regex, if there is one
            error("No previous pattern")
        # Determine where pattern stops = delim2
        escape = False
        for n, c in enumerate(comm[1:]):
            if c == "\\":
                escape = True
            elif c == "/" and not escape:
                delim2 = n
                break
        else:
            delim2 = len(comm)
        # search for pattern
        patt = re.compile(comm[1:delim2])
        for m, line in enumerate(\
              self.text[self.cursor:] + \
              self.text[:self.cursor]):
            if patt.search(visible(line)):
                matchline += m
                matchline %= len(self.text)
                break
        # check if pattern ends comm
        if delim2 >= len(comm) - 1:
            delim2 = -1
        return matchline, delim2

    def getAddress(self, comm):
        """Determine address at comm start, and where it stops or -1"""
        if len(comm) == 0:
            return -1, 0
        if   comm[0] in "/?":  addr, end = self.search(comm)
        elif comm[0] in "+-":  addr, end = self.cursor, 0
        elif comm[0] == "." :  addr, end = self.cursor, 1
        elif comm[0] == "$" :  addr, end = max(0, len(self.text) - 1), 1
        elif isDigit(comm[0]): addr, end = self.getNumber(comm)
        else:
            # No address, on non-empty command
            return -1, 0
        # Determine relative offset (if needed) and update end
        if end != -1:
            rel, relend = self.getRelative(comm[end:])
            addr += rel
            if relend == -1:
                end = -1
            else:
                end += relend
        # Return address, if legal
        if 0 <= addr < len(self.text):
            return addr, end
        error("Invalid address")

    def getRange(self, comm):
        addr, end = self.getAddress(comm)
        if end == -1:
            if addr == -1:
                # empty comm
                return [], -1
            else:
                # comm == single address
                return [addr], -1
        elif end == 0:
            # empty address
            if comm[0] == ",":
                # nothing left of comma
                addr = 0
            else:
                # no range before command
                return [], 0
        if comm[end] != ",":
            # single address, not range, before command
            return [addr], end
        addr2, end2 = self.getAddress(comm[end+1:])
        if addr2 == -1:
            # nothing right of comma
            addr2 = len(self.text) - 1
        elif addr2 < addr:
            error("Invalid address")
        if end2 == -1:
            # comm == range
            return [addr, addr2], -1
        # range, followed by command
        return [addr, addr2], end + 1 + end2

    def empty(self, rng):
        if len(rng) == 0:
            self.cursor += 1
        else:
            self.cursor = rng[-1]
        return visible(self.text[self.cursor])

    def updateMarks(self, rng, inc):
        if not self.marks:
            return
        for n, i in enumerate(reversed(self.marks)):
            if i >= rng[0]:
                if i <= rng[-1]:
                    del self.marks[-n-1]
                else:
                    self.marks[-n-1] += inc

    def print(self, rng, hide=True):
        if len(rng) == 0:
            rng = [self.cursor]
        for line in sub(self.text, rng):
            yield visible(line) + "\n"

    def printHidden(self, rng):
        if len(rng) == 0:
            rng = [self.cursor]
        for line in sub(self.text, rng):
            yield complete(line) + "\n"
        if rng[-1] == max(0, len(self.text) - 1):
            for n, line in enumerate(self.appendix):
                yield "{}{}\033[m".format(st, line)

    def enumerate(self, rng):
        if len(rng) == 0:
            rng = [self.cursor]
        for n, line in enumerate(sub(self.text, rng)):
            yield "{:6d}  {}\n".format(n+1, visible(line))

    def enumerateHidden(self, rng):
        if len(rng) == 0:
            rng = [self.cursor]
        for n, line in enumerate(sub(self.text, rng)):
            parts = complete(line).split("\n")
            for hiddenline in parts[:-1]:
                yield "\t" + hiddenline
            #yield "\033[m"
            yield "{:6d}  {}\n".format(n+1, parts[-1])
        if rng[-1] == max(0, len(self.text) - 1):
            yield st
            for line in self.appendix:
                yield "\t" + line
            yield "\033[m"

    def insert(self, rng):
        """insert before line"""
        if len(rng) == 0:
            line = self.cursor
        else:
            line = rng[0]
        newText = self.newText or getText()
        if len(newText) > 0:
            self.modified = True
        self.text[line:line] = newText
        self.updateMarks([line], len(newText))
        self.cursor = line + len(newText) - 1
        if self.cursor == -1:
            # inserted nothing, before beginning
            self.cursor = 0

    def append(self, rng):
        """append after line"""
        # TODO : should appending after last line
        # cause appendix to be merged before new content ?
        if len(rng) == 0:
            line = self.cursor
        else:
            line = rng[-1]
        if len(self.text) == 0:
            self.cursor = -1
        newText = self.newText or getText()
        if len(newText) > 0:
            self.modified = True
        self.text[line+1:line+1] = newText
        self.updateMarks([line], len(newText))
        self.cursor = line + len(newText)

    def change(self, rng):
        """change line range (or cursor)"""
        self.delete(rng)
        self.insert([])

    def delete(self, rng):
        """delete line range (or cursor)"""
        self.modified = True
        if len(rng) == 0:
            rng = [self.cursor]
        for n, line in reversed(nsub(self.text, rng)):
            if type(line[0]) == type([]) and \
               line[0][0][-1] == "\n":
                line = line[0] + [merge(line[1:]) + "\n"]
            else:
                line = [merge(line) + "\n"]
            if n < len(self.text) - 1:
                # merge line to beginning of next
                nextline = self.text[n+1]
                if type(nextline[0]) == type([]) and \
                   nextline[0][0][-1] == "\n":
                    nextline[0] = line + nextline[0]
                else:
                    nextline = [line] + nextline
                self.text[n:n+2] = [nextline]
            else:
                self.appendix = line + self.appendix
                self.text[-1:] = []
        self.updateMarks(rng, rng[0] - rng[-1] - 1) # Decrement by rng.len
        self.cursor = rng[0]
        if self.cursor == len(self.text):
            self.cursor = len(self.text) - 1

    def glob(self, rng, comm):
        if len(rng) == 0:
            rng = [0, len(self.text)-1]
        if len(comm) == 1:
            error("Invalid pattern delimiter")
        if len(comm) == 2:
            # TODO repeat previous search pattern, if available
            error("No previous pattern")
        delim = comm[1]
        esc = False
        for n, c in enumerate(comm[2:]):
            if esc: # Skip current character
                esc = False
            elif c == "\\":
                esc = True
            elif c == delim:
                delim2 = n+2
                break
        else:
            delim2 = len(comm)
        if esc:
            error("Trailing backslash (\\)")
        subcomms = comm[delim2+1:].split("\n")
        newTexts = []
        for n, subcomm in enumerate(subcomms):
            if subcomm == "":
                subcomms[n] = "p"
            elif subcomm[-1] in "gGvV":
                error("Cannot nest global commands")
            elif subcomm[-1] in "iac":
                if n + 1 == len(subcomms):
                    del subcomms[n]
                    break
                newTexts.append([])
                for m, line in enumerate(subcomms[n+1:]):
                    if line == ".":
                        subcomms[n+1:n+2+m] = []
                        break
                    newTexts[-1].append([line])
                else:
                    subcomms[n+1:] = []
        if len(subcomms) == 0: # i.e. "<rng>g/<re>/[iac]"
            return
        firstsubcomm = subcomms[0]
        patt = re.compile(comm[2:delim2])
        self.marks = []
        for n in rng:
            if patt.search(visible(self.text[n])):
                self.marks.append(n)
        while len(self.marks) > 0:
            subcomms[0] = str(self.marks[0]+1) + firstsubcomm
            del self.marks[0] # Even if line not modified :-P
            newTextIdx = 0
            for subcomm in subcomms:
                if subcomm[-1] in "iac":
                    self.newText = newTexts[newTextIdx]
                    self.parse(subcomm)
                    newTextIdx += 1
                    self.newText = False
                else:
                    self.parse(subcomm)
        self.marks = False

    def substitute(self, rng, comm):
        if len(rng) == 0:
            rng = [self.cursor]
        if len(comm) == 1:
            # TODO repeat previous substitution, if there is one
            error("No previous substitution")
        delim = comm[1]
        # TODO replace this with an FSA to avoid escaped delimiters
        delim2 = comm.find(delim, 2)
        if delim2 == -1:
            error("Invalid pattern delimiter")
        patt = re.compile(comm[2:delim2])
        # Determine replacement string and substitution count
        # TODO replace this with an FSA to avoid escaped delimiters
        delim3 = comm.find(delim, delim2+1)
        cnt = 1
        if delim3 == -1:
            repl = comm[delim2+1:]
        else:
            repl = comm[delim2+1:delim3]
            if delim3 + 1 == len(comm):
                pass
            elif comm[delim3+1:] == "g":
                cnt = 0
            elif all(map(isDigit, comm[delim3+1:])):
                cnt = int(comm[delim3+1:])
            else:
                error("Invalid command suffix")
        globmatched = False
        for n, line in nsub(self.text, rng):
            # TODO for sub count != 1 repeat the whole thing
            # warning : avoid regex recursion !!!
            vis = ""
            matched = False
            for m, part in enumerate(line):
                if type(part) == type([]):
                    continue
                vis += part
                match = patt.search(vis)
                if not match:
                    continue
                # there is a match !
                globmatched = matched = True
                if len(vis) - match.start() > len(part):
                    # goes across hidden content, change line
                    hid = ""
                    for part in line:
                        if type(part) == type([]):
                            if part[0][-1] == "\n":
                                continue
                            for hidden in part[0]:
                                hid += hidden # TODO distinguish bits ?
                        else:
                            hid += part
                    hid += "\n"
                    newline = patt.sub(repl, visible(line), 1)
                    if type(line[0]) == type([]) and \
                       line[0][0][-1] == "\n":
                        # there already are hidden lines
                        line = [line[0] + [hid], newline]
                    else:
                        # there is no hidden line yet
                        line = [[hid], newline]
                else:
                    # change in place
                    start = match.start() - (len(vis) - len(part))
                    end   = match.end()   - (len(vis) - len(part))
                    if start == end: # zero-length matches ("^", "$")
                        line[m] = patt.sub(repl, line[m])
                    else:
                        newparts = []
                        if part[:start] != "":
                            newparts.append(part[:start])
                        newparts.append([part[start:end]])
                        newparts.append(patt.sub(repl, part[start:end]))
                        if part[end:] != "":
                            newparts.append(part[end:])
                        # actual insertion
                        line[m:m+1] = newparts
                    # TODO attempt merges (recursive ?) outside of part
                    # TODO allow newlines
                break
            if matched:
                self.cursor = rng[0] + n
                self.text[self.cursor] = line
        self.updateMarks(rng, 0)
        if globmatched:
            self.modified = True
            return visible(self.text[self.cursor]) + "\n"
        else:
            error("No match")

    def join(self, rng):
        """join range (or [cursor, cursor+1])"""
        if len(rng) == 0:
            if self.cursor + 1 == len(self.text):
                error("Invalid address")
            rng = [self.cursor, self.cursor + 1]
        newline = self.text[rng[0]][:]
        for line in sub(self.text, [rng[0]+1, rng[-1]]):
            if type(newline[-1]) == type([]) and \
               type(line[0]) == type([]):
                newline[-1].extend(line[0])
                newline.extend(line[1:])
            else:
                newline.extend(line)
        self.text[rng[0]:rng[-1]+1] = [newline]
        self.updateMarks(rng, rng[0] - rng[-1]) # decrement by rng.len - 1
        self.cursor = rng[0]

    def debug(self, rng):
        yield str(self.text) + "\n"
        yield str(self.appendix) + "\n"

    def printLine(self, rng):
        """print last line in range or cursor"""
        if len(rng) == 0:
            rng = [self.cursor]
        return str(rng[-1])

    def printHelp(self, rng):
        return help

    def quit(self, rng):
        """quit (fail on non-empty line range)"""
        if len(rng) > 0:
            error("Unexpected address")
        if self.modified and not self.override:
            self.override = True
            error("Warning: buffer modified")
        sys.exit(0)

    def quitforce(self, rng):
        """quit (fail on non-empty line range)"""
        if len(rng) > 0:
            error("Unexpected address")
            return
        sys.exit(0)

    def parse(self, comm):
        rng, end = self.getRange(comm)
        if end == -1: comm = ""
        else:         comm = comm[end:]
        if comm != "q": # two consecutive "q"s force quit
            self.override = False
        if len(comm) <= 1:
            commtab = {
                "" : self.empty,
                "q": self.quit,
                "" : self.empty,
                "q": self.quit,
                "Q": self.quitforce,
                "p": self.print,
                "P": self.printHidden,
                "n": self.enumerate,
                "N": self.enumerateHidden,
                "%": self.debug,
                "i": self.insert,
                "a": self.append,
                "c": self.change,
                "d": self.delete,
                "j": self.join,
                "=": self.printLine,
                "h": self.printHelp
            }
            # Call command, or build generator
            gen = commtab[comm](rng)
            if gen:
                for line in gen:
                    print(line, end="")
        else:
            if comm[0] == "g":
                while comm[-1] == "\\":
                    comm = comm[:-1] + "\n" + input("")
                # Assume glob returns nothing
                self.glob(rng, comm)
            elif comm[0] == "s":
                sys.stdout.write(self.substitute(rng, comm) or "")
            else:
                error("Unknown command")

    def edit(self):
        print("type h for help")
        while True:
            try:
                comm = input(">")
                self.parse(comm)
            except EdError as e:
                sys.stdout.write("\033[7m{}\033[m\n".format(e.msg))
