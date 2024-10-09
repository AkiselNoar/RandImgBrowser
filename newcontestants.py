#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys, os, re
from pathlib import Path
from random import sample
from collections import defaultdict
from itertools import combinations
from functools import lru_cache
from statistics import mean

from Contestant import *

@lru_cache(None)
def check_names(origin=".", debug=False):
    d = defaultdict(list)
    for p in filter(lambda x: x.is_file(), Path(origin).glob("*")):
        n, *_ = p.stem.split('_')
        d[n].append(p)

    if debug:
        for name, paths in d.items():
            if len(paths) > 1:
                print("==", name, "==")
                print(*paths, sep=os.linesep)

    return d

def normalize(o, d):
    op = d
    check_names.cache_clear()
    o = check_names(o)
    d = check_names(d)

    for a in filter(lambda a: a in d, o):
        for p in o[a]:
            print(p, "to", op)
            if '--dry' not in sys.argv and p.is_file():
                p.rename(Path(op, p.name))

def select_new(n, orig, dest):
    d = check_names(orig)
    assert len(d) >= n
    for e in sample(list(d), n):
        print(e, "entering", dest)
        for p in d[e]:
            p.rename(Path(dest, p.name))

@orm.db_session
def do_count(league_dirs):
    print(f"{'League':<11}", f"{'Nb_cont':<6}", end=" ")
    print('App(min/max/avg) Points Top')
    for p in league_dirs:
        print(f"{str(p):<11}", f"{len(check_names(p)):<6}", end=" ")
        l = [c.appearances for c in Contestant.select(lambda x: x.league==p.name)]
        if not l:
            print()
            continue
        l_pts = [c.pts() for c in Contestant.select(lambda x: x.league==p.name)]
        head = max([c for c in Contestant.select(lambda x: x.league==p.name)], key=lambda c: c.pts())
        if l:
            print(f"{min(l)}/{max(l)}/{mean(l):.2f} {mean(l_pts):>7.2f} {head.name:<20} {head.pts():>7.2f}")
        else:
            print(0)

@orm.db_session
def rename(old, new):
    if old == new:
        print("same arguments given")
        return
    d = dict()
    for p in filter(os.path.isdir, os.listdir('.')):
        d.update(check_names(p))

    if old not in d:
        print(old, "not present in folders")
    else:
        for p in d[old]:
            p.rename(str(p).replace(old, new))


    oold = Contestant.get(name=old)
    if not oold:
        print("old", old, "not in db")
    else:
        onew = Contestant.get(name=new)
        if not onew:
            print("new", new, "not in db")
            newd = oold.to_dict()
            newd["name"] = new
            onew = Contestant(**newd)
            oold.delete()
        else:
            try:
                onew.points += oold.points
                onew.appearances += oold.appearances
                oold.delete()
            except AttributeError:
                print("attribute error")

@orm.db_session
def releague(leagues_dir):
    for d in leagues_dir:
        m = check_names(d)
        d = Path(d).name
        for n in m:
            c = Contestant.get(name=n)
            if c:
                c.league = d

@orm.db_session
def print_nfo(leagues_dir, name):
    r = re.compile(f'.*{name}.*')
    for d in leagues_dir:
        m = check_names(d)
        for con in m:
            if r.match(con):
                print(con, len(m[con]),
                        *set(p.parent for p in m[con]), end=" ")
                con = Contestant.get(name=con)
                if con:
                    print(f"{con.appearances}App {con.pts():.2f}Pts")
                else:
                    print()

def main():
    leagues_path = Path(".league_dirs")
    leagues_dir = list()
    noleague_source = list()
    alldirs = list()
    if not leagues_path.is_file():
        print("Not in a tournament dir")
        return
    promo = list()
    re_m = re.compile(r"^-(.+?)->(.+?)$")
    for l in leagues_path.read_text().splitlines():
        l = l.strip()
        if not l or l.startswith('#'):
            continue
        m = re_m.search(l)
        if m:
            promo = m.groups()
            continue
        if l.startswith('-'):
            l = l[1:]
            noleague_source.append(Path(l).expanduser())
        alldirs.append(Path(l).expanduser())

    leagues_dir = [d for d in alldirs if d not in noleague_source]

    noout = False
    if "--noout" in sys.argv:
        sys.argv.remove("--noout")
        noout = True
    if len(sys.argv) == 2 and sys.argv[1].isdigit():
        #New contestants from default promotion to default promotion
        select_new(int(sys.argv[1]), *promo)
    if len(sys.argv) == 2 :
        #Info on contestant
        print_nfo(leagues_dir, sys.argv[1])
        return
    elif len(sys.argv) == 3 and sys.argv[1].isdigit():
        #New contestants from default promotion to arg
        select_new(int(sys.argv[1]), promo[0], sys.argv[2])
    elif len(sys.argv) == 4 and sys.argv[1].isdigit():
        #New contestants from arg to arg
        select_new(int(sys.argv[1]), sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 3:
        #Rename contestant from 1 to 2
        rename(*sys.argv[1:])

    for o, d in combinations(alldirs, 2):
        normalize(o, d)
    releague(leagues_dir)
    if not noout:
        do_count(leagues_dir)


if __name__ == "__main__":
    bind()
    main()
