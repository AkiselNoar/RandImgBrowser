#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, sys

from random import shuffle, choice
from pathlib import Path

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from .browserbase import QImg, BrowserBase

from string import ascii_uppercase as alpa
from itertools import *
from collections import *
from glob import glob

from .Contestant import *

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
        self.img_a.set_img(str(a))
        self.img_b.set_img(str(b))
        self.lbl_a.setText(str(a.name.split('_')[0]))
        self.lbl_b.setText(str(b.name.split('_')[0]))
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

class AbcImgFight(QObject):
    def __init__(self, ihm_cls, ihm=None):
        super().__init__()
        self.commit = False
        self.ihm = ihm or ihm_cls()
        self.ihm.win = self.win
        self.side = ""
        self.nxt = self.gen_nxt()
        next(self.nxt)

    def vs(self, a, b):
        self.current_duel = [a, b]
        shuffle(self.current_duel)
        self.winner = None
        self.ihm.title = [self.side]
        self.ihm.set_img(*self.current_duel)

    def win(self, i):
        winner, looser = self.current_duel if not i else self.current_duel[::-1]
        winner.win(looser)
        try:
            next(self.nxt)
        except StopIteration:
            self.end()

    def end(self):
        self.commit = True
        self.state()
        app.quit()

    def state(self):
        print("winners :", len(self.winners), *(w.name for w in self.winners))
        print("loosers :", len(self.loosers), *(w.name for w in self.loosers))
        print("dropped :", len(self.dropped), *(w.name for w in self.dropped))

def seed(contestants=None, size=0):
    contestants = list(contestants)
    shuffle(contestants)
    contestants = sorted(contestants, key=lambda c: c.appearances) #least most common first
    if size > len(contestants):
        raise Exception(f"not enought contestants, ({size} > {len(contestants)})")
    contestants = contestants[:size] #No More than size contestants
    return sorted(contestants, key=lambda c: c.pts(), reverse=True) #Seeding

class ImgLeague(AbcImgFight):
    def __init__(self, ihm_cls=VSImg, ihm=None, choosens=None):
        if not choosens:
            raise
        nb_grp = 16
        grp_size = 5
        contestants = seed(contestants=choosens, size=grp_size*nb_grp)
        print(*contestants, sep='\n')
        ll_tmp_file = "/tmp/last_league.txt"
        with open(ll_tmp_file, 'w') as f:
            print(*[c.name for c in contestants], sep='\n', file=f)
            print(ll_tmp_file, "file written")
        for c in contestants:
            c.appearances += 1
        self.winners = list()
        self.loosers = list()
        self.dropped = list()
        self.groups = [contestants[i::nb_grp] for i in range(nb_grp)]
        super().__init__(ihm_cls, ihm=ihm)

    @pyqtSlot()
    def end(self):
        self.commit = True
        #rev = ImgTourRev(winners=self.dropped, ihm=self.ihm, parent=self)
        rev = ImgTour(winners=self.winners, ihm=self.ihm, parent=self)

    def rev_end(self):
        m = len(self.loosers)//2
        loosers = self.loosers[m:] + self.loosers[:m]
        ImgTour(winners=self.winners, loosers=loosers, ihm=self.ihm)

    def gen_nxt(self):
        for i, g in enumerate(self.groups):
            self.current_group = g
            self.side = f"Groupe {alpa[i]}"
            self.wins = list()
            yield from self.do_grp(g)
            counter = Counter(x for x, _ in self.wins)
            g = sorted(g, key=lambda c: counter[c], reverse=True)
            for i, c in enumerate(g[::-1]):
                c.points += i

            print(self.side, ":", *g)
            self.winners.extend(g[:2])
            self.loosers.append(g[2])
            self.dropped.extend(g[3:])

    def win(self, i):
        winner, looser = self.current_duel if not i else self.current_duel[::-1]
        idxw, idxl = self.current_group.index(winner), self.current_group.index(looser)
        if idxl > idxw:
            self.current_group[idxl], self.current_group[idxw] = winner, looser
        self.wins.append((winner, looser))
        super().win(i)

    def do_grp(self, group):
        l = list(combinations(group, 2))
        shuffle(l)
        for a, b in l:
            yield self.vs(a, b)

class ImgTour(AbcImgFight):
    def __init__(self, winners=list(), loosers=list(), dropped=list(), ihm_cls=VSImg, ihm=None, parent=None):
        self.winners = winners
        self.loosers = loosers
        self.dropped = dropped
        super().__init__(ihm_cls=ihm_cls, ihm=ihm)

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

    def win(self, i):
        winner, looser = self.current_duel if not i else self.current_duel[::-1]
        if self.side.startswith("Loosers"):
            winner.points += 1
            self.loosers.append(winner)
            self.dropped.append(looser)
        elif self.side.startswith("Winners"):
            winner.points += 2
            self.winners.append(winner)
            self.loosers.append(looser)
        if "Grand Final" in self.side:
            winner.points += 3
        super().win(i)

    def gen_nxt(self, looser_side=False):
        while len(self.winners) > 1:
            if looser_side:
                self.side = "Loosers"
                while len(self.loosers) > len(self.winners)/2:
                    yield from self.do_round(self.loosers, len(self.winners)/2)
            self.side = "Winners"
            yield from self.do_round(self.winners)
            self.loosers.reverse()

        if looser_side:
            self.side = "Loosers Finals"
            yield from self.do_round(self.loosers)
            self.side = "Winners Grand Final :"
            yield self.vs(self.winners.pop(), self.loosers.pop())


class ImgTourRev(ImgTour):
    ended = pyqtSignal()
    def __init__(self, winners=list(), loosers=list(), dropped=list(), ihm_cls=VSImg, ihm=None, parent=None):
        self.parent = parent
        super().__init__(winners, loosers, dropped, ihm_cls, ihm)

    def gen_nxt(self, looser_side=True):
        self.side = "Droppeds"
        while len(self.winners) > 1:
            yield from self.do_round(self.winners)
            self.loosers.reverse()

    def win(self, i):
        winner, looser = self.current_duel if not i else self.current_duel[::-1]
        looser.points -= 1
        self.dropped.append(winner)
        self.winners.append(looser)
        AbcImgFight.win(self, i)

    def end(self):
        self.parent.rev_end()
        self.commit = True

def main():

    bind()
    ihm_cls = VSImg
    choosens = set()
    with orm.db_session:
        for p in map(Path, sys.argv[1:]):
            print("loading", p)
            if p.is_dir():
                for f in p.glob('*'):
                    name, *_ = f.stem.split('_')
                    c = Contestant.get(name=name)
                    if not c:
                        c = Contestant(name=name)
                    *_, c.league = p.stem.split('_')
                    c.append_paths(f)
                    choosens.add(c)
            elif p.is_file():
                name, *_ = p.stem.split('_')
                c = Contestant.get(name=name)
                if not c:
                    c = Contestant(name=name)
                *_, c.league = p.parent.stem.split('_')
                c.append_paths(p)
                choosens.add(c)

        if not choosens:
            print("no Contestant founds ?")
            exit(1)


        m = ImgLeague(ihm_cls=ihm_cls, choosens=choosens)
        app.exec_()
        if not m.commit:
            orm.rollback()
        else:
            orm.commit()
            print("max", max(v.id for v in VS.select()))
            print("saving")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main()
