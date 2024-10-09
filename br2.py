#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, sys
from copy import copy
from pathlib import Path
import browse_rand as BR
from math import log2

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

def get_progress_spill(orig, dest):
    orig = Path(orig)
    dest = Path(dest)
    nb_o, nb_d = len(list(orig.glob('*'))), len(list(dest.glob('*')))
    objective = nb_o / 2

    return nb_d / objective

class Bank2(BR.Bank):
    _progress = 0
    objective = 1

    def __next__(self):
        folder = Path(self.imgs[0]).parent
        sub_folder = folder / "NextStep"
        while get_progress_spill(folder, sub_folder) < 1:
            try:
                return next(self._imgs)
            except StopIteration:
                self.reload()
                if not self:
                    raise ValueError("No More Image to browse")
        app.quit()

class Main(BR.Main):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bank = Bank2(args[1], recursive=kwargs.get("recursive"))

    def update_title(self):
        if self.img:
            img = Path(self.img)
            folder = img.parent
            sub_folder = folder / "NextStep"
            self.title = f"{folder.stem} {img.stem.split('_')[0]} {(1+self.hist.idx)%(len(self.bank)+1)}/{len(self.bank)} {get_progress_spill(folder, sub_folder)*100:.2f}"
        super().update_title(self.title)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    if os.path.isfile("def.css"):
        with open("NWLib/def.css", 'r') as f:
            app.setStyleSheet(f.read())
    path = Path(os.environ["HOME"], "Downloads")
    time = 10000
    rec = 1
    args = copy(sys.argv)
    paths = list()
    for a in args:
        if os.path.isdir(a) or os.path.isfile(a):
            paths.append(Path(a).absolute())
            sys.argv.remove(a)
        elif a.isdigit() or (a.startswith('-') and a[1:].isdigit()):
            rec = int(a)
        elif a.startswith('-t'):
            time = int(a[2:])
    Main(rec<0, paths, time=time).show()
    sys.exit(app.exec_())

