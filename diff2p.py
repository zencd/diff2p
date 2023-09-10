#!/usr/bin/python
import math
from io import StringIO
import os
import re
import sys
import subprocess


def read_process_output(args):
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    return proc.communicate()[0].decode('utf-8')


class LineReader:
    def __init__(self, f):
        self.f = f
        self.lines_read = 0

    def read_line(self, line_no_1_based=None):
        if line_no_1_based is not None:
            assert self.lines_read + 1 == line_no_1_based, 'lines_read=%s, line_no_1_based=%s' % (
                self.lines_read, line_no_1_based)
        line = self.f.readline().strip()
        if line is not None:
            self.lines_read += 1
        return line


def make_file_reader(fname):
    if not os.path.exists(fname):
        raise Exception('file %s does not exist' % fname)
    return LineReader(open(fname))


def make_string_reader(string):
    return LineReader(StringIO(string))


def make_int_or_none(s):
    return s if s is None else int(s)


class ConsoleUI:
    def __init__(self, screen_width):
        w = screen_width - 2
        w1 = math.floor(w / 2)
        w2 = w - w1

        self.wrap = False
        self.left_width = w1
        self.right_width = w2
        # self.format_str = '|\033[93m%%-%ds\033[0m|%%-%ds|' % (self.left_width, self.right_width)
        self.format_left = '%%-%ds' % self.left_width
        self.format_right = '%%-%ds' % self.right_width

        format_left_colored = '%%-%ds' % (self.left_width + 9)
        self.sync_line_left = format_left_colored % '\033[44m \033[0m'

        format_right_colored = '%%-%ds' % (self.right_width + 9)
        self.sync_line_right = format_right_colored % '\033[44m \033[0m'

        self.normal_delim_left = '|'
        self.normal_delim_right = ' '
        # self.exceeded_delim = '\033[91m}\033[0m'
        self.exceeded_delim = '\033[41;37m}\033[0m'

        self.tab_replacement = ' ' * 4

    def print_two_panels(self, line1, line2, sed_change=False):
        # print self.format_str % (line1, line2)
        # sys.stdout.write('|')

        line1 = line1 if line1 is None else line1.replace('\t', self.tab_replacement)
        line2 = line2 if line2 is None else line2.replace('\t', self.tab_replacement)

        exceeded1 = False
        exceeded2 = False
        if self.wrap:
            raise Exception('wrapping is not implemented yet')
        else:
            if line1 and len(line1) > self.left_width:
                line1 = line1[0:self.left_width]
                exceeded1 = True
            if line2 and len(line2) > self.right_width:
                line2 = line2[0:self.right_width]
                exceeded2 = True

        if line1:
            s = self.format_left % line1
            if sed_change:
                # s = '\033[33m%s\033[0m' % s
                s = '\033[46;30m%s\033[0m' % s
                # s = '\033[7m%s\033[0m' % s
            sys.stdout.write(s)
        else:
            sys.stdout.write(self.sync_line_left)

        sys.stdout.write(self.exceeded_delim if exceeded1 else self.normal_delim_left)

        if line2:
            s = self.format_right % line2
            if sed_change:
                # s = '\033[33m%s\033[0m' % s # 93m
                s = '\033[46;30m%s\033[0m' % s  # 93m
            sys.stdout.write(s)
        else:
            sys.stdout.write(self.sync_line_right)

        sys.stdout.write(self.exceeded_delim if exceeded2 else self.normal_delim_right)
        print('')


def pass_equal_lines_before_current_action(start1, start2, in1, in2, continue_if_1, continue_if_2):
    while True:
        line1 = in1.read_line() if continue_if_1(in1.lines_read, start1) else None
        line2 = in2.read_line() if continue_if_2(in2.lines_read, start2) else None
        if line1 or line2:
            ui.print_two_panels(line1, line2)
        else:
            break


def sed_change(start1, end1, start2, end2, in1, in2):
    # print 'sed command "c"', start1, end1, start2, end2
    range1 = end1 - start1 + 1
    range2 = end2 - start2 + 1

    # print equal lines before current sed action
    continue_1_2 = lambda lines_read, action_start: lines_read + 1 < action_start
    pass_equal_lines_before_current_action(start1, start2, in1, in2, continue_1_2, continue_1_2)

    # print actual difference
    range_max = max(range1, range2)
    for i in range(range_max):
        line1 = in1.read_line() if i < range1 else None
        line2 = in2.read_line() if i < range2 else None
        ui.print_two_panels(line1, line2, sed_change=True)


def sed_delete(start1, end1, start2, end2, in1, in2):
    # something is deleted in the 2nd source
    # print 'sed command "d"', start1, end1, start2, end2
    assert start2 == end2
    _sed_delete_or_append(start1, end1, start2, end2, in1, in2, is_delete=True)


# something is added within the 2nd source
def sed_append(start1, end1, start2, end2, in1, in2):
    # print 'sed command "a"', start1, end1, start2, end2
    assert start1 == end1
    _sed_delete_or_append(start1, end1, start2, end2, in1, in2, is_delete=False)


def _sed_delete_or_append(start1, end1, start2, end2, in1, in2, is_delete):
    continue_if_1 = lambda lines_read, action_start: lines_read + 1 < action_start
    continue_if_2 = lambda lines_read, action_start: lines_read + 0 < action_start
    if not is_delete:
        (continue_if_1, continue_if_2) = (continue_if_2, continue_if_1)
    pass_equal_lines_before_current_action(start1, start2, in1, in2, continue_if_1, continue_if_2)

    startx = start1 if is_delete else start2
    endx = end1 if is_delete else end2
    for i in range(startx, endx + 1):
        line1 = in1.read_line(i) if is_delete else None
        line2 = in2.read_line(i) if not is_delete else None
        ui.print_two_panels(line1, line2)


def print_tails(in1, in2):
    # when all the sed actions are exhausted, then call this function to print the rests of the sources
    while True:
        line1 = in1.read_line()
        line2 = in2.read_line()
        if line1 or line2:
            ui.print_two_panels(line1, line2)
        else:
            break
    # pass_equal_lines_before_current_action()


sed_commands = {
    'c': sed_change,
    'd': sed_delete,
    'a': sed_append,
}


def parse_diff(diff_text, input1, input2):
    in1 = make_file_reader(input1)
    in2 = make_file_reader(input2)
    diff_reader = make_string_reader(diff_text)
    SED_ACTION_REGEX = re.compile('(\d+)(,(\d+))?' + '([cda])' + '(\d+)(,(\d+))?')
    while True:
        line = diff_reader.read_line()
        if not line: break
        m = re.match(SED_ACTION_REGEX, line)
        if m:
            start1 = make_int_or_none(m.group(1))
            end1 = make_int_or_none(m.group(3))
            sed_cmd = m.group(4)
            start2 = make_int_or_none(m.group(5))
            end2 = make_int_or_none(m.group(7))

            # convert '1c4' to '1,1c4,4'
            if end1 is None: end1 = start1
            if end2 is None: end2 = start2

            sed_commands[sed_cmd](start1, end1, start2, end2, in1, in2)
            # print 'matched:', sed_cmd, start1, end1, start2, end2
        elif re.match('[<>-].*', line):
            pass
        else:
            print('error: unexpected line reading diff: %s' % line)
    print_tails(in1, in2)


if __name__ == '__main__':
    input1 = sys.argv[1]
    input2 = sys.argv[2]

    try:
        size = read_process_output(['stty', 'size'])
        # print(f"size: {size}")
        width = int(size.strip().split(' ')[1])
    except IndexError:
        # stty not available in IDE
        width = 80

    ui = ConsoleUI(width)

    diff_text = read_process_output(['diff', input1, input2])
    parse_diff(diff_text, input1, input2)
