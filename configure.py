#!/usr/bin/python3
import os
import logging
import sys
import argparse
import pickle

def file_timestamp(path):
    st = os.stat(path)
    return st.st_mtime

class Incomplete(Exception):
    pass

class Configure:
    LESSON_DIR = "lessons"
    DOCUMENT_FILENAME = "document.tex"
    SLIDES_ENV_FILENAME = "slides-env.tex"
    SLIDES_FILENAME = "slides.tex"
    SLIDES_ENV_TEMPLATE = r"""
\newcommand{{\authorname}}{{{author_name}}}
\newcommand{{\authormail}}{{\texttt{{<{author_mail}>}}}}
\newcommand{{\extratitlepageline}}{{{extra_line}}}
"""
    SLIDES_TEMPLATE = r"""
\input{{../../common/slides-head.tex}}
\input{{../../common/"""+SLIDES_ENV_FILENAME+r"""}}
\newcommand{{\lessonno}}{{{0:d}}}
\newcommand{{\lessonnoo}}{{{0:02d}}}
\input{{../../common/slides-conf.tex}}

\input{{document.tex}}
"""

    MAKEFILE_HEADER = """\
LATEX=pdflatex -halt-on-error
COMMON_DEPS=configure.py
SLIDES_COMMON_DEPS=common/slides-*.tex
SLIDES="""+SLIDES_FILENAME+"""

default: slides
"""

    LESSON_SLIDES_TARGET = """\
lesson-slides-{lesson_no:02d}: {rel_path}/${{SLIDES}} {rel_path}/"""+DOCUMENT_FILENAME+""" ${{SLIDES_COMMON_DEPS}} ${{COMMON_DEPS}}
\tcd {rel_path}; $(LATEX) $(SLIDES) && $(LATEX) $(SLIDES)
"""

    MAKEFILE_FOOTER = """\
configure.py:
\t./configure.py
"""

    REQUIRED_FILES = [DOCUMENT_FILENAME]

    def __init__(self, base_path,
            force_rebuild=False,
            **env_upd):
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
        self.env_file = os.path.join(self.base_path, "configure.env")
        self.env = {
            "author_name": r"\\authorname",
            "author_mail": r"\\authormail",
            "extra_line": r""
        }
        if os.path.isfile(self.env_file):
            try:
                with open(self.env_file, "rb") as f:
                    self.pickled_env = pickle.load(f)
                self.env.update(self.pickled_env)
            except (IOError, OSError) as err:
                logging.warn("could not restore pickle'd state: %s", err)
                os.unlink(self.env_file)
                pass
        self.env.update(env_upd)
        try:
            with open(self.env_file, "wb") as f:
                pickle.dump(self.env, f)
        except (IOError, OSError) as err:
            logging.warn("could not save pickle'd state: %s", err)
        logging.debug("LaTeX substitution env: %r", self.env)

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
                lesson_no,
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
        slides_env_file = os.path.join(self.base_path, "common", self.SLIDES_ENV_FILENAME)
        with open(slides_env_file, "w") as f:
            f.write(self.SLIDES_ENV_TEMPLATE.format(**self.env))
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

    parser = argparse.ArgumentParser(
        description="""\
Create a Makefile and some auxilliary documents to build the slides for the
lessons. Autodiscovers lessons in ./lessons/, looking for directory names which
can be represented as an integer number. Directories must contain the neccessary
files, otherwise the build will fail (with appropriate error messages). You need
at least a `content.tex` file which contains the frame environments.

You dont have to pass the personalization arguments on each call to
configure.py, as the state is saved to configure.env."""
    )
    parser.add_argument(
        "-B", "--force-rebuild",
        dest="force_rebuild",
        action="store_true",
        default=False,
        help="Force rebuild of all files created by this program."
    )
    parser.add_argument(
        "-A", "--author-name",
        dest="author_name",
        help="LaTeX sourcecode to represent the authors name. Defaults to \
\\\\authorname."
    )
    parser.add_argument(
        "--author-mail",
        dest="author_mail",
        help="E-Mail adress to contact the author. Defaults to \\\\authormail."
    )
    parser.add_argument(
        "--extra-line",
        dest="extra_line",
        help="Line to show below the default title page stuff."
    )
    parser.add_argument(
        "-v",
        dest="verbosity",
        action="append_const",
        default=[],
        const=1,
        help="Increase verbosity level."
    )

    args = parser.parse_args()

    verbosity = len(args.verbosity)
    args.verbosity = None

    verbosity = max(0, min(2, verbosity))

    level = {
        0: logging.WARN,
        1: logging.INFO,
        2: logging.DEBUG
    }

    logging.basicConfig(level=level[verbosity],
                        format='%(levelname)-8s %(message)s')

    configure = Configure(
        os.getcwd(),
        **dict((k, v) for k, v in args._get_kwargs() if v is not None)
    )
    try:
        configure.autodiscover_lessons()
        configure.configure_lessons()
    except Incomplete:
        print("Configure incomplete.")

