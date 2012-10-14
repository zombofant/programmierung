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

   [1]: http://wiki.neo-layout.org/browser/latex/Standard-LaTeX/
