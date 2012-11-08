#!/usr/bin/python3
# encoding=utf-8
import subprocess
import re
import sys
import argparse

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    PASSED = '\033[01;32m'
    WARNING = '\033[93m'
    CANNOT_PASS = '\033[01;31m'
    EMPH = '\033[01m'
    ENDC = '\033[0m'

    def disable(self):
        self.EMPH = ''
        self.HEADER = ''
        self.OKBLUE = ''
        self.PASSED = ''
        self.WARNING = ''
        self.CANNOT_PASS = ''
        self.ENDC = ''

MIN_SUBMISSIONS = 9
MAX_SUBMISSIONS = 11
MIN_UNIT = 3
MAX_UNIT = 13

MAX_POINTS_PER_SUBMISSION = 6.0

MAX_POINTS = 55.0
MIN_POINTS = MAX_POINTS * 0.6

MAX_MISSING_SUBMISSIONS = 2

"""
contains commits which are to be ignored and should not produce any
warning output.
"""
commitWhitelist = [
]
looseMatch = re.compile("[0-9a-f]{40} (Amm?ended correction|corrected|imported).*", re.I)
ignore = re.compile("[0-9a-f]{40} (Merge|((Amm?ended )?[Ss]ubmission|\[ignore\])).*", re.I)
extractCommitId = re.compile("^[0-9a-f]{40}", re.I)
corrected = re.compile("([0-9a-fA-F]{40}) (Amm?ended correction( of)?|corrected|imported):? (([0-9]{1,2})/(\w+)|(\w+)/([0-9]{1,2}))\W?\s*(([0-9.]+)\s*\+\s*([0-9.]+)\s*=)?\s*([0-9.]+)?(\s+pts)?", re.I)

class Acknowledgement(object):
    def __init__(self, unit, person, points, style):
        self.unit = unit
        self.person = person
        self.points = points
        self.style = style

    def __str__(self):
        return "{0}/{1}: {2} pts".format(self.unit, self.person, self.points)

class PersonData(object):
    def __init__(self, person):
        self.person = person
        self.pointSum = 0
        self.submissions = []
        self.style = 0

    def add(self, ack):
        if ack.points is not None:
            self.pointSum += ack.points
            self.style += ack.style
            self.submissions.append((ack.unit, ack.points))

    def passed(self):
        return self.pointSum >= MIN_POINTS and len(self.submissions) >= MIN_SUBMISSIONS

    def canPass(self, currentUnit):
        remainingUnits = MAX_UNIT - currentUnit
        return ((MIN_SUBMISSIONS - (len(self.submissions) + remainingUnits)) <= 0, ((self.pointSum - MIN_POINTS) + remainingUnits * MAX_POINTS_PER_SUBMISSION) >= 0)

    def mayPass(self, currentUnit):
        remainingUnits = MAX_UNIT - currentUnit
        if len(self.submissions) == 0:
            avgPts = 0.
        else:
            avgPts = sum((submission[1] for submission in self.submissions))/len(self.submissions)
        return (avgPts, (MIN_POINTS-self.pointSum) <= remainingUnits * avgPts)

class ColoredString(object):
    def __init__(self, value, color):
        self.value = value
        self.color = color

class DataColumn(object):
    def __init__(self, heading, index, align = None, dataType = None, fill = None, precision = None):
        self.heading = heading
        self.index = index
        self.align = align
        self.dataType = dataType
        self.fill = fill
        self.precision = precision

    def _buildFmtStr(self, width = None):
        fmt = "{"+str(self.index)
        if (self.align or self.dataType or self.fill or self.precision or width) is not None:
            fmt += ':'
            if self.align is not None:
                if self.fill is not None:
                    fmt += self.fill
                fmt += self.align
            if width is not None:
                fmt += str(width)
            if self.precision is not None:
                fmt += '.'+str(self.precision)
            if self.dataType is not None:
                fmt += self.dataType
        return fmt+"}"

    def formatHLine(self, width):
        return "─"*width

    def getWidth(self, data):
        return max(len(self.heading), len(self._buildFmtStr().format(*data)))

    def formatHeading(self, width = None):
        return ("{0:"+str(width)+"s}").format(self.heading) if width is not None else self.heading

    def format(self, data, width = None):
        return self._buildFmtStr(width).format(*data)

class ColorColumn(DataColumn):
    def __init__(self, *args, **kwargs):
        super(ColorColumn, self).__init__(*args, **kwargs)
        self.actualIndex = self.index
        self.index = 0

    def getWidth(self, data):
        item = data[self.actualIndex]
        return super(ColorColumn, self).getWidth((item.value, ))

    def format(self, data, width = None):
        item = data[self.actualIndex]
        s = super(ColorColumn, self).format((item.value, ), width)
        return item.color + s + bcolors.ENDC

class SpacerColumn(object):
    def __init__(self, spacer, hlineSpacer = None):
        self.spacer = spacer
        self.hlineSpacer = hlineSpacer or spacer

    def formatHLine(self, width):
        return self.hlineSpacer

    def getWidth(self, data):
        return len(self.spacer)

    def format(self, data, width = None):
        return self.spacer

    def formatHeading(self, width = None):
        return self.spacer

class Tabular(object):
    def __init__(self, *columns):
        self.columns = list(columns)

    def render(self, dataMatrix):
        widths = [0] * len(self.columns)
        for row in dataMatrix:
            if row is None:
                continue
            for i, col in enumerate(self.columns):
                currWidth = col.getWidth(row)
                if currWidth > widths[i]:
                    widths[i] = currWidth

        heading = ""
        hline = ""
        rows = [""]*len(dataMatrix)
        for width, col in zip(widths, self.columns):
            heading += col.formatHeading(width)
            hline += col.formatHLine(width)
            for i, row in enumerate(dataMatrix):
                if row is None:
                    rows[i] += col.formatHLine(width)
                else:
                    rows[i] += col.format(row, width)

        print(heading)
        print(hline)
        for row in rows:
            print(row)

def parseCommits():
    git = subprocess.Popen(["git", "log", "--format=oneline"],
        stdout=subprocess.PIPE)
    (output, error) = git.communicate()
    if git.returncode != 0:
        print("Git returned with a nonzero return code. Exiting and propagating return code.", file=sys.stderr)
        sys.exit(git.returncode)
    output = output.decode("utf-8", errors="ignore")
    lines = output.split("\n")
    commitWhitelistMatchCount = 0
    acknowledgements = []
    for line in lines:
        if looseMatch.match(line) is None:
            if ignore.match(line) is None and not (len(line.rstrip().lstrip()) == 0):
                commitIdMatch = extractCommitId.search(line)
                if commitIdMatch is None or not commitIdMatch.group(0) in commitWhitelist:
                    print("Line does not match loose match, ignoring: ", file=sys.stderr)
                    print(line, file=sys.stderr)
                else:
                    commitWhitelistMatchCount += 1
            continue
        match = corrected.match(line)
        if match is None:
            print("Error: No match on required line.", file=sys.stderr)
            print(line, file=sys.stderr);
            sys.exit(1)

        groups = match.groups()
        if groups[0] in commitWhitelist:
            commitWhitelistMatchCount += 1
            continue

        unit = None
        person = None
        if groups[4] is None:
            unit = int(groups[7])
            person = groups[6]
        else:
            unit = int(groups[4])
            person = groups[5]
        points = None
        style = 0
        if unit >= MIN_UNIT:
            if groups[-2] is None:
                points = float(groups[-4]) + float(groups[-3])
                style = float(groups[-3])
            else:
                points = float(groups[-2])
        if points == 0:
            print("Not acknowledging {0}. Zero points.".format(groups[0]), file=sys.stderr)
            continue
        acknowledgements.append(Acknowledgement(unit, person, points, style))

    if commitWhitelistMatchCount > 0:
        print("Ignored {0} commits which were on the whitelist.".format(commitWhitelistMatchCount), file=sys.stderr)
    return acknowledgements

def filterAcknowledgements(acknowledgements):
    filterSet = set()
    for ack in acknowledgements:
        t = (ack.unit, ack.person)
        if t in filterSet:
            continue
        filterSet.add(t)
        yield ack

def getPersonData(acknowledgements):
    personMap = {}
    maxUnit = 0
    maxNameLen = 0
    for ack in acknowledgements:
        personData = personMap.setdefault(ack.person, PersonData(ack.person))
        if (ack.unit > maxUnit):
            maxUnit = ack.unit
        if (len(ack.person) > maxNameLen):
            maxNameLen = len(ack.person)
        personData.add(ack)
    return (sorted(personMap.values(), key=lambda x: x.person), maxUnit, maxNameLen)

def printData(personData, currentUnit, maxNameLen, showState):
    remainingUnits = (MAX_UNIT - currentUnit)
    print("The {0}{2}th{1} unit out of {0}{3}{1} has passed. Thus, {0}{4}{1} are remaining.".format(bcolors.EMPH, bcolors.ENDC, currentUnit, MAX_UNIT, remainingUnits))
    print("Currently, {0}{2:4.1f}{1} more points can be reached.".format(bcolors.EMPH, bcolors.ENDC, remainingUnits * MAX_POINTS_PER_SUBMISSION))
    # print("One can still pass with an amount of at least {0} submissions.".format(MAX_UNIT - currentUnit))
    print("Current results:")
    """nameheading = "Surname"
    if len(nameheading) > maxNameLen:
        maxNameLen = len(nameheading)
    namefmt = str(maxNameLen)+"s"
    print(("{2:"+namefmt+"} {0} Pts {1} Pts% {1} PtsMiss {1} Subs {1} Subs% {1} SubsMiss {1} State").format(
        "║",
        "│",
        nameheading
    ))
    print(("{2:"+namefmt+"} {0} """

    defaultSpacer = SpacerColumn(" │ ", "─┼─")
    table = Tabular(
        ColorColumn("name", 0),
        SpacerColumn(" ║ ", "─╫─"),
        ColorColumn("pts", 1, precision="4"),
        defaultSpacer,
        DataColumn("rel", 2, precision="2"),
        defaultSpacer,
        DataColumn("avg", 8, precision="3"),
        defaultSpacer,
        ColorColumn("miss", 3),
        defaultSpacer,
        ColorColumn("avgneed", 9, precision="3"),
        defaultSpacer,
        ColorColumn("units", 4),
        defaultSpacer,
        DataColumn("rel", 5, precision="2"),
        defaultSpacer,
        ColorColumn("miss", 6)
    )
    if showState:
        table.columns.append(defaultSpacer)
        table.columns.append(ColorColumn("state", 7))

    dataMatrix = []

    totalPts = 0.
    totalAvg = 0.
    totalSubsCount = 0
    totalMissingPts = 0.
    totalMissingSubs = 0
    totalNeededAvg = 0.
    totalStyle = 0.

    for person in personData:
        pts = person.pointSum
        subs = len(person.submissions)
        canPassBySubmissions, canPassByPoints = person.canPass(currentUnit)
        avgPts, mayPassByPoints = person.mayPass(currentUnit)
        color = ""
        state = ""
        if person.passed():
            color = bcolors.PASSED
            state = "passed"
        elif not (canPassBySubmissions and canPassByPoints):
            color = bcolors.CANNOT_PASS
            state = "failed"
        elif not mayPassByPoints:
            color = bcolors.WARNING
            state = "unlikely"
        else:
            color = bcolors.OKBLUE
            state = "okay"
        # print("{0}{1}{2}".format(color, person.person, bcolors.ENDC))

        ptscolor = bcolors.ENDC
        ptsmissingcolor = bcolors.ENDC
        if (pts >= MIN_POINTS):
            ptscolor = bcolors.PASSED
        elif not canPassByPoints:
            ptsmissingcolor = bcolors.CANNOT_PASS
        elif not mayPassByPoints:
            ptscolor = bcolors.WARNING

        subscolor = bcolors.ENDC
        subsmissingcolor = bcolors.ENDC
        if (subs >= MIN_SUBMISSIONS):
            subscolor = bcolors.PASSED
        elif not canPassBySubmissions:
            subsmissingcolor = bcolors.CANNOT_PASS

        missingPts = max(0., MIN_POINTS - pts)
        missingSubs = max(0, MIN_SUBMISSIONS - subs)
        neededAvg = missingPts / remainingUnits if remainingUnits > 0 else float("NaN")

        dataMatrix.append((
            ColoredString(person.person, color),
            ColoredString(float(pts), ptscolor),
            (float(pts) / MIN_POINTS),
            ColoredString(missingPts, ptsmissingcolor),
            ColoredString(subs, subscolor),
            (float(subs) / MIN_SUBMISSIONS),
            ColoredString(missingSubs, subsmissingcolor),
            ColoredString(state, color),
            float(avgPts),
            ColoredString(float(neededAvg), ptsmissingcolor)
        ))

        totalPts += pts
        totalSubsCount += subs
        totalAvg += avgPts
        if canPassByPoints:
            totalMissingPts += max(0., MIN_POINTS - pts)
        if canPassBySubmissions:
            totalMissingSubs += max(0., MIN_SUBMISSIONS - subs)
        totalNeededAvg += neededAvg
        totalStyle += person.style

    if len(dataMatrix) > 0:
        totalAvg /= len(dataMatrix)
        totalNeededAvg /= len(dataMatrix)
    dataMatrix.append(None)
    dataMatrix.append((
        ColoredString("total", ""),
        ColoredString(totalPts, ""),
        float('nan'),
        ColoredString(totalMissingPts, ""),
        ColoredString(totalSubsCount, ""),
        float('nan'),
        ColoredString(totalMissingSubs, ""),
        ColoredString("", ""),
        totalAvg,
        ColoredString(totalNeededAvg, bcolors.CANNOT_PASS if totalNeededAvg > MAX_POINTS_PER_SUBMISSION else bcolors.ENDC)
    ))

    table.render(dataMatrix)
    try:
        print("Average style points: {0}".format(totalStyle / totalSubsCount))
    except ZeroDivisionError:
        pass

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description="""
Parses git commit messages and calculates some statistics for the students.
Students are automatically added as they're found in the commitlog. Only the
newest commit for given unit and student tuple is taken into account. For
supported commit message formats, see below.""",
    epilog="""Supported commit formats:

    Corrected UNIT/NAME: PTS1 + PTS2 = PTSSUM
    Amended correction UNIT/NAME: PTS1 + PTS2 = PTSSUM
    Imported UNIT/NAME: PTS1 + PTS2 = PTSSUM

where UNIT is the decimal number of the unit which was corrected, NAME is the
name of the student (only one word), PTS1 is the number of main points which
were achieved, PTS2 is the number of additional points which were achieved and
PTSSUM is the sum of the points achieved (this is checked, so don't mess with
it).
""")

parser.add_argument(
    '-s', '--show-state',
    action='store_true',
    dest='showState',
    help="Show an additional column describing the state of the student (one \
of okay, unlikely, failed, passed)"
)
parser.add_argument(
    '-c', '--csv',
    action='store_true',
    dest='csvOutput',
    help="Give the relevant data in CSV output. Columns are headed properly, \
in German though."
)
parser.add_argument(
    '-n', '--no-color',
    action='store_true',
    dest='noColor',
    help="Do not use ANSI colour codes in the output."
)
args = parser.parse_args(sys.argv[1:])
if args.noColor:
    bcolors.disable(bcolors)

acknowledgements = list(filterAcknowledgements(parseCommits()))
personData, maxUnit, maxNameLen = getPersonData(acknowledgements)
if args.csvOutput:
    print('"Nachname","Punkte","Abgaben","bestanden"')
    for person in personData:
        print('"{0}","{1}","{2}","{3}"'.format(person.person, person.pointSum, len(person.submissions), person.passed()))
else:
    printData(personData, maxUnit, maxNameLen, args.showState)
