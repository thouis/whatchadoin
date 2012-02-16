# Author: Thouis (Ray) Jones
# License: BSD

from AppKit import NSWorkspace
import Quartz.CoreGraphics
import subprocess
import time
import sys
import PIL.Image
import PIL.ImageDraw
import PIL.ImageChops
import math
from collections import OrderedDict


def get_idle_time():
    output = subprocess.check_output(['ioreg', '-c', 'IOHIDSystem'])
    val = 0
    for l in output.split('\n'):
        if 'IdleTime' in l:
            val = int(l.split(' ')[-1])
    return val / 1000000000.0


def update_image(path, current_active, width=500, height=75, data=[('blah', 1, 'black')]):
    try:
        im = PIL.Image.open(path)
        assert im.size == (width, height)
        # shift up one row
        im = PIL.ImageChops.offset(im, 0, -1)
    except:
        im = PIL.Image.new('RGB', (width, height))
    draw = PIL.ImageDraw.Draw(im)
    total_time = float(sum(d[1] for d in data))
    base = 0
    keybase = 10
    for d in data:
        w = int((width * d[1]) / total_time)
        if d is data[-1]:
            w = width - base
        draw.rectangle([(base, (2 * height) / 3), (base + w, height)], fill=d[2])
        base += w
    for d in data:
        # draw the key
        draw.rectangle([(keybase, height - 20), (keybase + 10, height - 10)], fill=d[2], outline='black')
        draw.text((keybase + 15, height - 20), d[0], fill='white' if d[0] == current_active else 'black')
        keybase += 20 + draw.textsize(d[0])[0]
    im.save(path, 'PNG')


default_colors = OrderedDict([('terminal', 'green'),
                              ('coding', "rgb(13, 152, 186)"),
                              ('email', 'blue'),
                              ('web', 'red'),
                              ('unknown', 'rgb(128,0,0)')])


def update_counts(current_app, window_name, idle_time, old_counts, delta_t, timeconst):
    # clasisfy usage
    dest = 'misc'
    idle_threshold = 10
    if current_app == 'Emacs':
        dest = 'coding'
        idle_threshold = 30  # Allow more thinking when editing
    elif 'CellProfiler' in window_name:
        dest = 'coding'
        idle_threshold = 30  # Allow more thinking when editing
    elif current_app == 'Terminal':
        dest = 'terminal'
    elif current_app == 'Google Chrome':
        if 'Gmail' in window_name:
            dest = 'email'
        elif any([s in window_name.lower() for s in ['py', 'github']]):
            dest = 'coding'
        else:
            dest = 'web'
    else:
        dest = 'unknown'
    if idle_time > idle_threshold:
        return old_counts
    for k in old_counts:
        old_counts[k] *= math.exp(- timeconst * delta_t)
    old_counts[dest] = old_counts.get(dest, 0.0) + delta_t
    return dest


winfilter = Quartz.CoreGraphics.kCGWindowListOptionOnScreenOnly | Quartz.CoreGraphics.kCGWindowListExcludeDesktopElements
timecounts = {}
timeconst = math.log(0.5) / 3600  # half-life of one hour

while True:
    last = time.time()
    time.sleep(1)
    active_app = NSWorkspace.sharedWorkspace().activeApplication()
    current_pid = active_app['NSApplicationProcessIdentifier']
    app = active_app['NSWorkspaceApplicationKey']
    windows = [x for x in Quartz.CoreGraphics.CGWindowListCopyWindowInfo(winfilter, 0) if x['kCGWindowOwnerPID'] == current_pid]
    win_names = [w['kCGWindowName'] for w in windows if w.get('kCGWindowName', None)]
    win_name = win_names[0] if win_names else ''
    curtime = time.time()
    active = update_counts(app.localizedName(), win_name, get_idle_time(), timecounts, min(curtime - last, 3.0), timeconst)
    update_image(sys.argv[1], active, data=[(k, timecounts[k], default_colors[k]) for k in default_colors if k in timecounts])
