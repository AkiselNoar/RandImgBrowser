#!/usr/bin/python3

import sys, re, os
from glob import glob
from time import time
from copy import copy
from pathlib import Path
from shutil import copy2

from enum import Enum
from random import *
from collections import OrderedDict

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

try:
    from .browserbase import BrowserBase
except ImportError:
    from browserbase import BrowserBase

from Anana import safe_move

class Hist:
    def __init__(self):
        self.hist = list()
        self.idx = -1

    @property
    def current(self):
        if self.idx < 0:
            self.idx = 0
            raise IndexError("Negative indexes not allowed")
        return self.hist[self.idx]

    def append(self, img):
        self.idx += 1
        self.hist.append(img)

    def next(self):
        if self.idx < len(self.hist)-1:
            self.idx += 1
        else:
            raise IndexError
        return self.current

    def prev(self):
        self.idx -= 1
        return self.current

    def delete(self, img):
        while img in self.hist:
            i = self.hist.index(img)
            self.hist.remove(img)
            if i <= self.idx:
                self.idx -= 1

    def replace(self, old, new):
        while old in self.hist:
            i = self.hist.index(old)
            self.hist[i] = new

def search_img(rex):
    res = list()
    re_rex = re.compile(rex)
    for r, _, fs in os.walk('.'):
        for f in map(lambda p: Path(r, p), fs):
            if re_rex.match(f.name):
                res.append(f)

    if not res:
        print("no", rex, "file found")
    return res



def search_model_name(names):
    founds = OrderedDict.fromkeys(names)
    for r, _, fs in os.walk('.'):
        for f in map(lambda p: Path(r, p), fs):
            fname = f.stem.split('_')[0]
            if fname in founds:
                founds[fname] = f
                if all(founds.values()):
                    break

        if all(founds.values()):
            break
    else:
        for k, _ in filter(lambda v: not all(v), founds.items()):
            print(k, "not found")
    return list(founds.values())

class SortOpt(Enum):
    NORMAL = 0
    SORT = 1
    SHUFFLE = 2

class Bank:
    def __init__(self, paths, recursive=False, sort=SortOpt.NORMAL, reverse=False):
        self.paths = paths
        self.sort = sort
        self.recursive = recursive
        self.reverse = reverse
        self.reload()

    def reload(self):
        f = list()
        for folder in self.paths:
            if os.path.isfile(folder):
                if folder.suffix == ".txt":
                    ls = list()
                    with open(folder) as fh:
                        for l in fh:
                            l, *_ = l.strip().split('#')
                            for n in l.split():
                                if n:
                                    if Path(n).exists():
                                        f.append(Path(n))
                                    else:
                                        ls.append(n)
                    f.extend(search_model_name(ls))
                else:
                    f.append(folder)
            else:
                f.extend(folder.rglob("*") if self.recursive else folder.glob("*"))
        self.imgs = list(filter(lambda p: p and p.is_file() and p.suffix in BrowserBase.EXTS,
                f))
        self._len = len(self.imgs)
        match self.sort:
            case SortOpt.NORMAL:
                pass
            case SortOpt.SORT:
                self.imgs = sorted(self.imgs)
            case SortOpt.SHUFFLE:
                shuffle(self.imgs)
            case _:
                raise ValueError(f"Expected a SortOpt, got {self.sort}")
        if self.reverse:
            self.imgs = self.imgs[::-1]
        self._imgs = iter(self.imgs)

    def delete_img(self):
        self._len -= 1

    def __iter__(self):
        return self

    def __next__(self):
        while 1:
            return next(self._imgs)

    def __len__(self):
        return self._len

class Main(BrowserBase):
    def __init__(self, paths=None, **kwargs):
        """
        kwargs:
            recursive: bool, default=False
            infinite: bool, default=False
            pause: bool, default=False
            reverse: bool, default=False
        """
        paths = paths or [os.getcwd()]
        self.infinite = kwargs.get("infinite", False)

        self.hist = Hist()
        self.bank = Bank(paths,
                         recursive=kwargs.get("recursive", False),
                         sort=kwargs.get("sort", SortOpt.NORMAL),
                         reverse=kwargs.get("reverse", False)
                         )
        if not self.bank:
            raise IndexError("No images to browse")

        self.img = None
        super().__init__(**kwargs)

        sg = QDesktopWidget().screenGeometry()

        self.r_w = QWidget()
        self.r_l = QHBoxLayout()
        self.r_w.setLayout(self.r_l)
        self.hl.addWidget(self.r_w)
        self.r_w.hide()
        self.r_le = QLineEdit()
        self.r_btn = QPushButton("Rename")
        self.r_le.returnPressed.connect(self.rename)
        self.r_btn.clicked.connect(self.rename)
        self.r_l.addWidget(self.r_le)
        self.r_l.addWidget(self.r_btn)

        self.s_w = QWidget()
        self.s_l = QHBoxLayout()
        self.s_w.setLayout(self.s_l)
        self.hl.addWidget(self.s_w)
        self.s_w.hide()
        self.s_lbl = QLabel("NN")
        self.s_lbl.setFixedWidth(20)
        self.s_cb = QComboBox()
        self.s_cb.setEditable(True)
        self.s_cb.lineEdit().returnPressed.connect(self.move_sort)
        self.s_a = QPushButton('+')
        self.s_a.clicked.connect(self.ask_path)
        self.s_btn = QPushButton("Move")
        self.s_btn.clicked.connect(self.move_sort)
        self.s_l.addWidget(self.s_lbl)
        self.s_l.addWidget(self.s_cb)
        self.s_l.addWidget(self.s_btn)
        self.s_l.addWidget(self.s_a)
        self.pp = self.pause
        self.update_title()

    def move_sort(self):
        self.s_w.hide()

        try:
            nn = safe_move(str(self.img), os.path.expanduser(self.s_cb.currentText()), copy=(self.s_lbl.text() == "CP"))
        except AssertionError:
            return
        print(self.s_lbl.text(), self.img, "to", nn)

        if self.s_lbl.text() == "MV":
            self.bank.delete_img()
            self.hist.delete(self.img)
        self.nxt_img()

        self.lbl.setFocus()
        self.pause = self.pp

    @property
    def s_path(self):
        return self.img.parent

    def up_s_cb(self):
        self.s_cb.clear()
        if self.s_path == Path("~/Downloads").expanduser():
            g = glob(str(Path("~/Sorted").expanduser() / "*"))
        else:
            g = glob(os.path.join(self.s_path, "*"))
        g = glob(os.path.join(self.s_path, "*"))

        self.s_cb.addItems(
                sorted(
                    [d for d in g
                        if os.path.isdir(d)],
                    key=lambda x: x.lower())
                + [os.path.realpath(self.s_path.parent), "~/Downloads"])

    def ask_path(self):
        name, v = QInputDialog.getText(self, "New Folder", "Name : ")
        if v:
            os.mkdir(os.path.join(self.s_path, name))
            self.up_s_cb()

    def rename(self):
        newname = self.img.parent / self.r_le.text()
        if self.img.suffix != newname.suffix:
            print(newname, "change exention ; expected", self.img.suffix)
            return
        self._rename(self.img, newname)
        self.r_w.hide()
        self.lbl.setFocus()
        self.pause = self.pp

    def _rename(self, old, new):
        os.rename(old, new)
        self.hist.replace(self.img, new)
        self.set_img(new)

    def set_img(self, img):
        super().set_img(str(img))
        self.img = img

    def rand_img(self):
        try:
            img = next(self.bank)
        except StopIteration:
            if self.infinite:
                self.bank.reload()
                img = next(self.bank)
            else:
                app.quit()
                return
        self.hist.append(img)
        self.set_img(img)

    def man_nav(self, d):
        p = self.pause
        self.pause = True
        if d:
            self.nxt_img()
        else:
            self.prv_img()
        self.pause = p

    def nxt_img(self):
        try:
            self.set_img(self.hist.next())
        except IndexError:
            try:
                self.rand_img()
            except ValueError as e:
                print(e)
                app.quit()

    def prv_img(self):
        try:
            i = self.hist.prev()
        except IndexError:
            return
        self.set_img(i)

    def update_title(self):
        try:
            self.title = f"{self.img} {1+((self.hist.idx)%(len(self.bank)))}/{len(self.bank)}"
        except ZeroDivisionError:
            self.title = "GenNameError"
        super().update_title()

    def ren_img(self):
        if self.r_w.isVisible():
            self.pause = self.pp
            self.r_w.hide()
        else:
            self.r_le.setFocus()
            nn = '_' + re.sub(r"[^A-Za-z0-9\.]", "_", self.img.name)
            self.r_le.setText(nn)
            self.r_le.setCursorPosition(0)
            self.pp = self.pause
            self.pause=True
            self.r_w.show()

    def srt_or_cpy(self, t):
        if self.s_w.isVisible():
            self.pause=self.pp
            self.s_w.hide()
        else:
            self.s_lbl.setText(t)
            self.up_s_cb()
            self.s_cb.setFocus()
            self.pp = self.pause
            self.pause=True
            self.s_w.show()

    def cpy_img(self):
        self.srt_or_cpy("CP")

    def srt_img(self):
        self.srt_or_cpy("MV")

    def del_img(self):
        self.pp = self.pause
        self.pause = True
        ok = QMessageBox.question(self, "Delete IMG",
                f"Are you sure you want to delete {self.img} ?",
                QMessageBox.Yes | QMessageBox.No)
        if ok == QMessageBox.Yes:
            print("RM", self.img)
            os.remove(self.img)

            self.bank.delete_img()
            self.hist.delete(self.img)
            self.nxt_img()
        self.pause = self.pp

    def save_img(self):
        return
        save_rep = Path("~/Images/Real/00_NewElite").expanduser()
        nimg = save_rep / Path(self.img).name
        copy2(self.img, nimg)

    def escape_focus(self):
        self.lbl.setFocus()
        self.pause = self.pp
        self.r_w.hide()
        self.s_w.hide()

    def keyPressEvent(self, event):
        menu = {Qt.Key_Escape: self.escape_focus,
                Qt.Key_N: self.ren_img,
                Qt.Key_E: self.save_img}
        super().keyPressEvent(event, menu)


def tst_hist():
    hist = Hist()
    for i in range(5):
        hist.append(i)

    for i in range(3):
        print(hist.prev())

    print(hist.next())
    for i in range(3):
        print(hist.prev())

    print(hist.prev())
    exit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    if os.path.isfile("def.css"):
        with open("def.css", 'r') as f:
            app.setStyleSheet(f.read())
    args = copy(sys.argv)
    paths = list()
    kwargs = dict()
    for a in args:
        if os.path.isdir(a) or os.path.isfile(a) or os.path.isfile(a) and a.endswith("txt") :
            paths.append(Path(a).absolute())
            sys.argv.remove(a)
        elif a.startswith('-t'):
            kwargs["to"] = int(a[2:])
        elif a.startswith("-"):
            for opt in a:
                match opt:
                    case "i":
                        kwargs["infinite"] = True
                    case "p":
                        kwargs["pause"] = True
                    case "1":
                        kwargs["recursive"] = True
                    case "r":
                        kwargs["reverse"] = True
                    case "s":
                        kwargs["sort"] = SortOpt.SORT
                    case "m":
                        kwargs["sort"] = SortOpt.SHUFFLE
                    case "c":
                        kwargs["use_copy"] = True
        else:
            paths.extend(search_img(a))

    Main(paths, **kwargs).show()
    sys.exit(app.exec_())
