#!/usr/bin/python3
import os
import logging
import sys

def file_timestamp(path):
    st = os.stat(path)
    return st.st_mtime

class Incomplete(Exception):
    pass


class Configure:
    LESSON_DIR = "lessons"
    SLIDES_FILENAME = "slides.tex"
    SLIDES_TEMPLATE = r"""
\input{{../../common/slides-head.tex}}

\newcommand{{\lessonno}}{{{0:d}}}
\newcommand{{\lessonnoo}}{{{0:02d}}}

\input{{../../common/slides-conf.tex}}
\input{{content.tex}}
\input{{../../common/slides-foot.tex}}
"""

    MAKEFILE_HEADER = """\
LATEX=pdflatex -halt-on-error
COMMON_DEPS=configure.py
SLIDES_COMMON_DEPS=common/slides-*.tex

default: slides
"""

    LESSON_SLIDES_TARGET = """\
lesson-slides-{lesson_no:02d}: {rel_path}/slides.tex {rel_path}/content.tex ${{SLIDES_COMMON_DEPS}} ${{COMMON_DEPS}}
\tcd {rel_path}; $(LATEX) slides.tex && $(LATEX) slides.tex
"""

    MAKEFILE_FOOTER = """\
configure.py:
\t./configure.py
"""

    REQUIRED_FILES = ["content.tex"]

    def __init__(self, base_path, force_rebuild=False):
        super().__init__()
        self.base_path = base_path
        try:
            self.last_build = file_timestamp(
                os.path.join(self.base_path, "Makefile")
            )
            last_script_change = file_timestamp(sys.argv[0])
            self.last_build = max(self.last_build, last_script_change)
        except OSError:
            self.last_build = None
        if force_rebuild:
            self.last_build = force_rebuild
        self.lessons = {}

    def check_lesson_directory(self, path):
        for filename in self.REQUIRED_FILES:
            if not os.path.isfile(os.path.join(path, filename)):
                logging.error("missing %s", filename)
                return False
        return True

    def autodiscover_lessons(self):
        path = os.path.join(self.base_path, self.LESSON_DIR)
        for filename in os.listdir(path):
            try:
                lesson_no = int(filename)
            except ValueError:
                # not a valid lesson directory
                logging.warn("found garbage directory name: `%s'", filename)
                continue
            full_path = os.path.join(path, filename)
            if not self.check_lesson_directory(full_path):
                logging.error("lesson directory `%s' is missing files", filename)
                raise Incomplete()
            self.lessons[lesson_no] = full_path

    def create_slides_file(self, lesson_no, lesson_path):
        slides_path = os.path.join(lesson_path, self.SLIDES_FILENAME)
        try:
            if file_timestamp(slides_path) >= self.last_build:
                return
        except TypeError:
            # self.last_build is None
            pass
        except OSError:
            pass

        with open(slides_path, "w") as f:
            f.write(self.SLIDES_TEMPLATE.format(
                lesson_no
            ))

    def configure_lesson(self, lesson_no, path):
        logging.info("configuring lesson %d", lesson_no)
        self.create_slides_file(lesson_no, path)

    def final_touch(self, path, timestamp):
        fullpath = os.path.join(path, self.SLIDES_FILENAME)
        os.utime(fullpath, (timestamp, timestamp))

    def final_touches(self, timestamp):
        for path in self.lessons.values():
            self.final_touch(path, timestamp)

    def configure_lessons(self):
        for lesson_no, path in self.lessons.items():
            self.configure_lesson(lesson_no, path)
        timestamp = self.create_makefile()
        self.final_touches(int(timestamp))

    def create_makefile(self):
        logging.info("writing Makefile")
        makefile = os.path.join(self.base_path, "Makefile")
        with open(makefile, "w") as f:
            f.write(self.MAKEFILE_HEADER)

            for lesson_no, path in self.lessons.items():
                rel_path = os.path.relpath(path, self.base_path)
                f.write(self.LESSON_SLIDES_TARGET.format(
                    lesson_no=lesson_no,
                    full_path=path,
                    rel_path=rel_path
                ))

            f.write("slides: {0}\n".format(
                " ".join("lesson-slides-{0:02d}".format(no) for no in self.lessons.keys())
            ))

            f.write(self.MAKEFILE_FOOTER)
        timestamp = int(file_timestamp(makefile))
        os.utime(makefile, (timestamp, timestamp))
        return timestamp


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)-8s %(message)s')

    configure = Configure(os.getcwd())
    try:
        configure.autodiscover_lessons()
        configure.configure_lessons()
    except Incomplete:
        print("Configure incomplete.")

