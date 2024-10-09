#!/usr/bin/python3

import sys, re, os
import shutil
from glob import iglob as glob
from copy import copy
from shutil import copyfile
from pathlib import Path

from collections import Counter

from random import *
from itertools import *

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from Anana import Consts
from browserbase import BrowserBase

class Img:
    def __init__(self, path, model):
        self.path = path
        self.name = os.path.basename(path)
        self.model = model
        self.src = path.split(os.path.sep)[0]

    def delete(self):
        print("removing", self.path)
        os.remove(self.path)

    def move(self, dest, keep=False, prefix=False, destname=None):
        if destname:
            nname = destname + Path(self.path).suffix
        else:
            nname = f"{os.path.basename(self.model)}_" * prefix + self.name
        print(["moving", "copying"][keep], self.path, "to", os.path.join(dest, nname))
        if keep:
            copyfile(self.path, os.path.join(dest, nname))
        else:
            os.rename(self.path, os.path.join(dest, nname))
        return nname

    def __eq__(self, other):
        return self.path == other.path

    def __str__(self):
        return f"{self.src} {self.name}"

    def __repr__(self):
        return self.path

class BankModel:
    def __init__(self, paths):
        self.paths = paths
        self.name = os.path.basename(paths[0])
        self._current = None

    def __iter__(self):
        self._lst = []
        for path, ext in product(chain(self.paths), BrowserBase.EXTS):
            self._lst.extend(glob(os.path.join(path, '**/*' + ext), recursive=True))
        return self

    @property
    def index(self):
        return "{}/{}".format(self._lst.index(self._current) + 1, len(self._lst))

    @property
    def current(self):
        return Img(self._current, self.name)

    def __next__(self):
        if not self._lst:
            raise StopIteration
        p = choice(self._lst)
        while not os.path.isfile(p):
            p = choice(self._lst)
        self._current = p
        return self.current

    def __str__(self):
        return self.name

class Bank:
    def __init__(self, p=[]):

        self._lst = {} #Lists of path
        self.model = None
        self.img = None
        self.lock_model = False

        if not p:
            p.append("all")

        for getp in [d for d in os.listdir() if os.path.isdir(d)]:
            getp = os.path.basename(getp)
            if 'all' in p or getp in p:
                l = 0
                print(getp, flush=True, end=" ... ")
                for m in os.listdir(getp):
                    pm = os.path.join(getp, m)
                    if m not in self._lst:
                        self._lst[m] = []
                    self._lst[m].append(pm)
                    l += 1
                print("done", l)
        print("done", len(self._lst))
        with open(Consts.HTA_PATH / "fromPopoMove.txt", 'w') as f:
            print(*self._lst.keys(), sep=os.linesep, file=f)

    def filter(self, func=None):
        if not func and not hasattr(self, "f_filter"):
            return
        self.f_filter = func or self.f_filter
        self._lst = dict(((k, v) for k, v in self._lst.items() if self.f_filter(k)))

    def __iter__(self):
        return self

    def set_model(self, paths):
        if isinstance(paths, str):
            paths = self._lst[paths]
        self.model = iter(BankModel(paths))

    def set_img(self, img):
        self.set_model(self._lst[img.model])
        self.model._current = img.path
        self.img = img

    def __next__(self):
        if not self.model or not self.lock_model:
            self.filter()
            self.set_model(choice(list(self._lst.values())))
        try:
            self.img = next(self.model)
        except StopIteration:
            print("no more imgs for", self.model.name)
            self.set_model(choice(list(self._lst.values())))
            self.lock_model = False
            self.img = next(self.model)
        return self.img

    def __contains__(self, key):
        return key in self._lst

    @property
    def title(self):
        return "{} {} {}".format(self.model.index, self.model, self.img)

class HistBank:
    def __init__(self, bank):
        self._hist = []
        self._index = -1
        self._lindex = -1
        self._lhist = []
        self._bank = bank

    @property
    def current(self):
        return self.hist[self.index]

    @property
    def hist(self):
        if self._bank.lock_model:
            if not self._lhist:
                self._lhist.append(self._hist[self._index])
                self._lindex += 1
            return self._lhist
        else:
            return self._hist

    @hist.setter
    def hist(self, value):
        if self._bank.lock_model:
            self._lhist = value
        else:
            self._hist = value

    @property
    def index(self):
        if self._bank.lock_model:
            return self._lindex
        else:
            return self._index

    @index.setter
    def index(self, value):
        if self._bank.lock_model:
            self._lindex = value
        else:
            self._index = value

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self, advance=True, model=None):
        if self._bank.lock_model or model:
            self._bank.lock_model = True
            try:
                self._bank.set_model(model or self.current.model)
            except IndexError:
                pass
        else:
            self._lhist = []
            self._lindex = -1

        if advance:
            self.index += 1
        try:
            no = self.current
            self._bank.set_img(no)
        except IndexError:
            no = next(self._bank)
            self.hist.append(no)

            #handle memory limit
            if len(self.hist) > 1000:
                self.hist = self.hist[-1000:]
                self.index = 999

        return no

    def prev(self):
        self.index = max(self.index-1, 0)
        n = self.next(False)
        self._bank.set_img(n)
        return n

    def delete(self):
        c = self.current
        self.next()
        c.delete()
        self.del_fromhist(c)

    def move(self, dest, keep=False, prefix=False, destname=False):
        c = self.current
        nn = self.current.move(dest, keep=keep, prefix=prefix, destname=destname)
        if not keep:
            self.next()
            self.del_fromhist(c)
        return nn

    def del_fromhist(self, bak):
        while bak in self._hist:
            if self._hist.index(bak) <= self._index:
                self._index -= 1
            self._hist.remove(bak)
        while bak in self._lhist:
            if self._lhist.index(bak) <= self._lindex:
                self._lindex -= 1
            self._lhist.remove(bak)



class Main(BrowserBase):
    def __init__(self):


        #Init saving zone
        self.save_zone = os.path.expanduser('~/Saved')
        self.saved = set()
        self.saved_c = Counter()
        self.bank = Bank(list(filter(lambda x: not x.startswith('-'), sys.argv[1:])))
        import sqlite3
        con = sqlite3.connect("/home/an/tmp/league_2.db")
        cur = con.cursor()
        cur.execute("select name, appearances from contestant;")
        for (n, a) in cur.fetchall():
            if n in self.bank:
                self.saved_c[n] = int(a)
        con.close()
        if not os.path.exists(self.save_zone):
            os.mkdir(self.save_zone)
        else:
            for f in os.listdir(self.save_zone):
                self.saved.add(f.split('_')[0])

        if '--nosaved' in sys.argv:
            self.bank.filter(lambda x: x not in self.saved and self.saved_c[x] <= min(self.saved_c.values()))
        self.hist = iter(HistBank(self.bank))

        BrowserBase.__init__(self)

    def prv_img(self):
        self.set_img(self.hist.prev().path)

    def nxt_img(self):
        self.set_img(self.hist.next().path)

    def look_for(self):
        model, ok = QInputDialog.getText(self, "FindModel", "Which Model are you looking for ?")
        if ok and model in self.bank:
            self.nxt_def(model)

    def nxt_def(self, model):
        self.set_img(self.hist.next(model=model).path)

    def update_title(self):
        title = list()
        if self.bank.lock_model:
            title.append("[L]")

        if self.bank.model.name in self.saved:
            title.append(f"{{{len(self.saved)//80};{100*(len(self.saved)%80)//80}}}")

        title.append(f"-{self.saved_c[self.bank.model.name]}a-")
        title.append(self.bank.title)
        self.title = ' '.join(title)
        super().update_title()

    def del_img(self):
        p = self.pause
        self.pause = True
        ok = QMessageBox.question(self, "Delete IMG",
                f"Are you sure you want to delete {self.hist.current} ?",
                QMessageBox.Yes | QMessageBox.No)
        if ok == QMessageBox.Yes:
            self.hist.delete()
            self.set_img(self.hist.current.path)
        self.pause = p

    def srt_img(self):
        p = self.pause
        self.pause = True
        ok = QMessageBox.question(self, "Resort IMG",
                f"Are you sure you want to reconsider {self.hist.current} ?",
                QMessageBox.No | QMessageBox.Yes)
        if ok == QMessageBox.Yes:
            self.hist.move(self.unsort_zone)
            self.set_img(self.hist.next().path)
        self.pause = p

    def sav_img(self):
        p = self.pause
        self.pause = True
        ok = QMessageBox.question(self, "SaveIMG",
                f"Are you sure you want to save {self.hist.current} ?",
                QMessageBox.No | QMessageBox.Yes)
        if ok == QMessageBox.Yes:
            nn = self.hist.move(self.save_zone, keep=True, prefix=True,)
            self.saved.add(nn.split("_")[0])
        self.pause = p

    def lck_model(self):
        self.bank.lock_model = not self.bank.lock_model

    def keyPressEvent(self, event):
        menu = {Qt.Key_L: self.lck_model,
                Qt.Key_E: self.sav_img,
                Qt.Key_F: self.look_for}
        super().keyPressEvent(event, menu)

class Mock(Main):
    def __init__(self):
        Main.__init__(self)

    def set_img(self, img):
        print(self.hist, end=" - ")
        if os.path.exists(img.path):
            self.lbl.setText(img.path)
            print(img.path)
        else:
            self.lbl.setText(img.path + " Not Found")
            print(img.path, "Not Found")

        self.update_title()

    def onResize(self, event):
        pass

def tst():
    bank = Bank()
    hist = iter(HistBank(bank))

    print()
    for i in range(5):
        print(hist.next().path, '\t', bank.title)
    print('--lockmodel')
    bank.lock_model = True
    hist.delete()
    for i in range(5):
        print(hist.next().path, '\t', bank.title)
    for i in range(5):
        print(hist.prev().path, '\t', bank.title)

if __name__ == "__main__":
    if os.getenv("kpath"):
        os.chdir(os.path.expanduser(os.getenv("kpath")))
    print(os.getcwd())
    if '--tst' in sys.argv:
        tst()
        sys.exit()
    app = QApplication(sys.argv)
    if os.path.exists("def.css"):
        with open("def.css", 'r') as f:
            app.setStyleSheet(f.read())
    if '--mock' in sys.argv:
        Mock().show()
    else:
        Main().show()
    sys.exit(app.exec_())
