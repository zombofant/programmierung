Programmierung
==============

These are materials for the Programmierung course of the physics department at
the Dresden University Of Technology. As the course is in german, the following
description will also be in german (as most of the contents themselves is).

Inhalt
------

Dieses Repository enthält hauptsächlich Folien für die Programmierungsübungen,
die als Grundlage für eigene Folien der jeweiligen Übungsleiter dienen sollen.
Es ist weder so gedacht noch erwünscht, dass Übungsleiter diese Folien einfach
übernehmen und in ihrer Übung herunterrattern. Statt dessen ist es erforderlich,
den Quelltext zu den Folien (im jeweiligen Verzeichnis unter dem Namen
``document.tex`` zu finden) gelesen zu haben, da dieser wichtige
Nebeninformationen enthält.

Verwendung
----------

Die Folien verwenden das ``uniinput.sty``-TeX-Paket, welches leider nicht in der
Standard-TeX-Distribution enthalten ist. Es muss manuell installiert werden
und ist auf der [Webseite des neo-Tastaturlayouts erhältlich][1].

Zunächst muss ein Klon des Repositories angelegt werden:

    $ git clone https://github.com/zombofant/programmierung
    $ cd programmierung

Danach muss das Makefile erzeugt und grundlegende Konfiguration vorgenommen
werden:

    $ ./configure.py --author-name "Ihr Name" \
                     --author-mail "ihr.name@example.com"

Wenn keine Fehler auftreten, können die Foilen nun mit dem ``make``-Befehl
erzeugt werden:

    $ make

Wenn nur die Folien zu einer bestimmten Übung erwünscht sind, z.B. zur Nullten
Übung:

    $ make lessons/00/slides.pdf

Ansonsten werden alle Folien gebaut (was einige Zeit dauern kann).

Struktur
--------

*   In ``common/`` liegen TeX-Sources die von allen Folien verwendet werden.
    Unter anderem landet dort die durch ``./configure.py`` vorgenommene
    Konfiguration.

*   In ``lessons/`` sollten nur Ordner mit ganzzahligem Namen liegen. Die Zahl
    gibt den Index der Übung an (z. B. ``lessons/04`` für die vierte Übung).
    ``configure.py`` durchsucht das Verzeichnis ``lessons`` und erstellt das
    Makefile anhand der vorhandenen Ordner.

    In den Übungsorndern muss mindestens eine ``document.tex`` liegen, welche
    das eigentliche LaTeX-Beamer-Dokument (inkl.
    ``\begin{document}..\end{document}``, aber ohne ``\documentclass``) enthält.

    Sollte diese Datei fehlen bricht ``configure.py`` mit einem Fehler ab!

*   ``configure.py`` bietet einige Einstellungsmöglichkeiten an, die in einem
    internen Format in ``configure.env`` gespeichert werden, sodass sie nicht
    bei jedem Aufruf von ``configure.py`` erneut angegeben werden müssen. Die
    ``configure.env``-Datei ist in der ``.gitignore`` eingetragen, bleibt also
    immer nur auf dem lokalen System.


   [1]: http://wiki.neo-layout.org/browser/latex/Standard-LaTeX/
