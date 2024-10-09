#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, sys

from random import shuffle, choice
from pathlib import Path

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from browserbase import QImg, BrowserBase

from itertools import cycle

import sqlite3
from Anana import getch

class IDB:

    DB_PATH = "/home/an/Dropbox/WR/NoNameTnmt.db"

    def __init__(self):
        self.con = sqlite3.connect("/home/an/Dropbox/WR/NoNameTnmt.db")
        self.cur = self.con.cursor()

    def execute(self, cmd, commit=True):
        self.cur.execute(cmd)
        if commit:
            self.con.commit()
        return self.cur.fetchall()

    def win(self, w, l):
        self.cur.execute(f"INSERT INTO VS(winner, looser) VALUES ('{w.name}', '{l.name}')")
        self.con.commit()

    all_goc = dict()
    def get_all(self, division):
        self.all_goc.clear()
        fields = ["id", "league", "appearances", "wc", "lc", "Contestants.name"]
        query = f"""SELECT Contestants.{', '.join(fields)} from Contestants
        inner join WinsCount on Contestants.id = WinsCount.id
        left join division_entry on Contestants.id = contestant and division_entry.name = '{division}'"""
        l = """where Contestants.name = '{c.name}'"""
        self.cur.execute(query)
        for l in self.cur.fetchall():
            d = dict(zip(fields, l))
            self.all_goc[d["Contestants.name"]] = d

    def get_or_create(self, c):
        if not self.all_goc:
            self.get_all(c.division)
        if c.name not in self.all_goc:
            print("--insertion")
            self.cur.execute(f"INSERT INTO Contestants(name) VALUES ('{c.name}')")
            self.con.commit()
            self.get_all(c.division)

        return self.all_goc[c.name]
        """ handling contestant in multiple division
            lr = list(l[0])
            for n in l[0:]:
                lr[2] += n[2]
            l = [lr]
        """

    def __del__(self):
        self.con.commit()
        self.con.close()

class Contestant:
    DB = IDB()
    FULL = dict()
    def __init__(self, path, name=None, division="One"):

        self.name = name or Path(path).stem.split('_')[0]
        if self.name in self.FULL:
            return
        self.FULL[self.name] = self

        self._path = Path(path)
        if self._path.is_dir():
            self._path = list(filter(lambda x: Path(x).suffix in BrowserBase.EXTS, self._path.glob("**/*")))

        self.division = division
        r = self.DB.get_or_create(self)
        if r:
            self.__dict__.update(r)
        self.division = division
        self.appearances = self.appearances or 0
        print(self.name, "Entered")

    def appeared(self):
        self.appearances += 1
        print(self.name, self.winpct, self.appearances)
        self.DB.execute(f'insert or ignore into division_entry (contestant, name) values ({self.id}, "{self.division}")', commit=0)
        self.DB.execute(f"UPDATE division_entry SET appearances= appearances+1 where contestant = {self.id} and name = '{self.division}'", commit=0)
        self.DB.con.commit()

    @property
    def path(self):
        return self._path if not isinstance(self._path, list) else choice(self._path)

    def win(self, looser):
        self.DB.win(self, looser)

    @property
    def winpct(self):
        try:
            return 100*self.wc/(self.wc + self.lc)
        except ZeroDivisionError:
            return 0

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<{self.__class__.__name__}{self.id}: {self.name}[{self.division}]>"

class VSImg(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowState(Qt.WindowMaximized)
        self.setStyleSheet("background-color: #14191B;color: #F5E9E0")
        self.title = list('.')

        #INIT IHM
        self.lbl_a = QLabel()
        self.lbl_b = QLabel()
        self.img_a = QImg()
        self.img_b = QImg()
        self.lbl_a.setMaximumHeight(25)
        self.lbl_b.setMaximumHeight(25)
        lbl = QLabel("vs")
        lbl.setAlignment(Qt.AlignCenter)
        self.lbl_a.setAlignment(Qt.AlignRight)
        self.lbl_b.setAlignment(Qt.AlignLeft)
        lbl.setMaximumHeight(25)
        lbl.setMaximumWidth(25)

        hl = self.hl = QGridLayout()
        hl.setSpacing(0)
        hl.setContentsMargins(0, 0, 0, 0)
        widget = QWidget()
        widget.setLayout(hl)
        self.setCentralWidget(widget)
        hl.addWidget(self.img_a, 1, 0)
        hl.addWidget(self.img_b, 1, 2)
        hl.addWidget(lbl, 0, 1)
        hl.addWidget(self.lbl_a, 0, 0)
        hl.addWidget(self.lbl_b, 0, 2)

        self.resizeEvent = self.onResize
        self.show()

    def onResize(self, event):
        pass

    def set_img(self, a, b):
        self.img_a.set_img(str(a.path))
        self.img_b.set_img(str(b.path))
        self.lbl_a.setText(a.name)
        self.lbl_b.setText(b.name)
        self.title.extend([a.name, ".vs.", b.name])
        self.update_title()

    def update_title(self):
        title = list('.') #Start title with a point to keep the process sitting in the task bar
        title.extend(self.title)
        self.setWindowTitle(' '.join(title))

    def keyPressEvent(self, event, menu={}):
        _menu = {Qt.Key_Right: lambda: self.win(1),
                Qt.Key_Left: lambda: self.win(0)}
        _menu.update(menu)
        try:
            _menu[event.key()]()
        except KeyError:
            pass
        self.update_title()

class ImgTour:
    def __init__(self, ihm_cls=VSImg):
        contestants = list(Contestant.FULL.values())
        print(contestants)
        print("shuffle", len(contestants))
        shuffle(contestants)
        print("sort")
        contestants = sorted(contestants, key=lambda c: c.appearances) #least most common first
        print("reduce")
        self.winners = contestants[:64] #No More than 64 contestants
        self.winners = sorted(self.winners, key=lambda c: c.winpct, reverse=True) #Seeding
        [c.appeared() for  c in self.winners]
        self.loosers = list()
        self.dropped = list()

        print("go")
        self.ihm = ihm_cls()
        self.ihm.win = self.win
        self.nxt = self.gen_nxt()
        next(self.nxt)


    def do_round(self, lst, limit=1):
        contestants = lst[:]
        lst.clear()

        #Extempt top seed from round is odd number of contestants
        l = len(contestants) % 2
        lst.extend(contestants[:l])
        contestants = contestants[l:]
        for _ in range(len(contestants)//2):
            #Pop last and first to respect seeding
            a = contestants.pop(0)
            b = contestants.pop()
            yield self.vs(a, b)
        lst.extend(contestants)

    def gen_nxt(self, looser_side=True):
        while len(self.winners) > 1:
            if looser_side:
                self.side = "Loosers"
                while len(self.loosers) > len(self.winners)/2:
                    yield from self.do_round(self.loosers, len(self.winners)/2)
            self.side = "Winners"
            yield from self.do_round(self.winners)

        if looser_side:
            self.side = "Loosers Finals"
            yield from self.do_round(self.loosers)
            self.side = "Winners Grand Final :"
            yield self.vs(self.winners.pop(), self.loosers.pop())

    def vs(self, a, b):
        self.current_duel = (a, b)
        self.winner = None
        self.ihm.title = [self.side]
        self.ihm.set_img(a, b)

    def win(self, i):
        if i:
            self.current_duel = self.current_duel[::-1]
        winner, looser = self.current_duel
        winner.win(looser)
        if self.side.startswith("Loosers"):
            self.loosers.append(winner)
            self.dropped.append(looser)
        elif self.side.startswith("Winners"):
            self.winners.append(winner)
            self.loosers.append(looser)
        try:
            next(self.nxt)
        except StopIteration:
            self.state()
            app.quit()

    def state(self):
        print("winners :", len(self.winners), *(w.name for w in self.winners))
        print("loosers :", len(self.loosers), *(w.name for w in self.loosers))
        print("dropped :", len(self.dropped), *(w.name for w in self.dropped))

if __name__ == "__main__":
    from glob import glob

    ihm_cls = VSImg
    app = QApplication(sys.argv)
    p = None
    try:
        p = Path(sys.argv[1])
        print(p, p.name)
    except IndexError:
        pass
    if p and p.name == "Saved":
        list(map(lambda x: Contestant(x, division="Saved"),
            glob("/home/an/Dropbox/Saved/*")))
    elif p and p.is_dir():
        list(map(lambda x: Contestant(x, division=p.stem), p.glob('*')))
    elif p and p.is_file():
        list(map(lambda x: Contestant(x, division=p.stem.capitalize()),
            (l.strip() for l in p.read_text().splitlines() if l.strip())
                ))
    else:
        list(map(lambda x: Contestant(x, division="One"),
            glob("/home/an/Sorted/0_Real/00_Noname4Chan/renamed/*")))

    if not Contestant.FULL:
        print("no Contestant founds ?")
        exit(1)


    ImgTour(ihm_cls)
    sys.exit(app.exec_())
