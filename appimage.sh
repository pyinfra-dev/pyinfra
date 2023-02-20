#!/bin/bash
pip install python-appimage
python-appimage install appimagetool &&
python-appimage install patchelf &&
python-appimage build app -p 3.11 ./appimage
