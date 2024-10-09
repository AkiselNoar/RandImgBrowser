#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os

from random import choice
from datetime import datetime

from pony import orm

db = orm.Database()

class Contestant(db.Entity):
    name = orm.PrimaryKey(str)
    points = orm.Optional(int, default=0)
    appearances = orm.Optional(int, default=0)
    league = orm.Optional(str, default="None")
    wins = orm.Set("VS", reverse="winner")
    losses = orm.Set("VS", reverse="looser")

    def get_vs(self):
        c = dict()
        for w in self.wins:
            l = w.looser
            if l not in c:
                c[l] = 0
            c[l] += 1
        for w in self.losses:
            w = w.winner
            if w not in c:
                c[w] = 0
            c[w] -= 1
        return c


    def pts(self):
        if not hasattr(self, "_pts"):
            self._pts = 0
            if self.nb_battles() != 0:
                c = self.get_vs()
                #print(*[f"{k.name} {v}" for k, v in c.items()], sep='\n')
                for k, v in c.items():
                    if v > 0:
                        self._pts += k.win_pct() * (v+1)
                    elif v < 0:
                        self._pts += (100 - k.win_pct()) * v
                    else:
                        self._pts += k.win_pct()
                self._pts /= self.nb_battles()
        return self._pts

    def append_paths(self, f):
        if not hasattr(self, "paths"):
            self.paths = list()
        self.paths.append(f)

    def win(self, looser):
        with open(os.path.expanduser("league.hist"), 'a') as f:
            print(datetime.now().isoformat(), self.name, '>', looser.name, file=f)
        VS(winner=self, looser=looser)

    def path(self):
        return choice(self.paths)

    def t(self):
        return len(self.paths)

    def i(self, o):
        return self.paths.index(o)

    def win_pct(self):
        if self.nb_battles() == 0:
            return 0.0
        if not hasattr(self, "_win_pct"):
            c = self.get_vs()
            self._win_pct = 100 * ((2*len([k for k, v in c.items() if v > 0])) + len([k for k, v in c.items() if v == 0])) / (2*len(c))
        return self._win_pct

    def nb_battles(self):
        if not hasattr(self, "_nb_battles"):
            self._nb_battles = len(self.wins) + len(self.losses)
        return self._nb_battles

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return f"{self.name}({self.appearances}) -{self.league}"

class VS(db.Entity):
    id = orm.PrimaryKey(int, auto=True)
    winner = orm.Required(Contestant)
    looser = orm.Required(Contestant)

def bind():
    db.bind(provider="sqlite", filename=os.path.expanduser('league.db'), create_db=True)
    db.generate_mapping(create_tables=True)

@orm.db_session
def main():
    print(Contestant.get(name=sys.argv[1]))

if __name__ == "__main__":
    bind()
    main()


