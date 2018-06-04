#!/usr/bin/env python

import argparse
import json
import os
import subprocess
import sys

import jinja2


def template_file(infile, outfile, kwargs):
    path, filename = os.path.split(infile)
    j2_env = jinja2.Environment(loader=jinja2.FileSystemLoader(path) or '.')
    result = j2_env.get_template(filename).render(**kwargs)

    with open(outfile, 'w') as f:
        f.write(result)


def base_name(outfile, infile):
    if not outfile:
        basefile = '.'.join(os.path.basename(
            os.path.abspath(infile)).split('.')[:-1])
    else:
        basefile = outfile
    basefile += '-plate'

    return basefile


def renderscad(args):
    basename = base_name(args.outfile, args.infile)

    scad_file = '%s.scad' % basename
    dxf_file = '%s.dxf' % basename

    cmd = 'openscad {scad} -o {dxf}'.format(scad=scad_file, dxf=dxf_file)
    cmd = cmd.split()

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    returncode = p.poll()

    sys.stdout.write(stdout)

    if returncode:
        sys.stderr.write('Error executing "%s"\n' % (' '.join(cmd)))
        sys.stderr.write(stderr)

        sys.exit(1)


def genscad(args, keydata):
    stab_type = '%s_stab' % args.stabs

    max_rows = len(keydata)
    keys = []
    stabs = []
    rects = []

    key_xofs = 0
    key_yofs = 0
    extra_height = 0
    extra_width = 0

    drills = []

    if args.ptype == 'sandwich':
        extra_height = args.bottompadding + args.toppadding
        extra_width = args.leftpadding + args.rightpadding

        key_xofs = args.leftpadding
        key_yofs = args.bottompadding

        if args.topscrews:
            extra_height = args.drillsize * 6
            key_yofs += args.drillsize * 3

        if args.sidescrews:
            extra_width += args.drillsize * 6
            key_xofs += args.drillsize * 3

    height = (19.05 * len(keydata)) + extra_height

    widths = []
    for ridx, row in enumerate(keydata):
        row_width = 0
        nextkey = 1
        nextheight = 1
        invert_stab = 'false'

        for key in row:
            if isinstance(key, dict):
                if 'w' in key:
                    nextkey = key['w']
                if 'h' in key:
                    nextheight = key['h']
                if '_rs' in key:
                    if key['_rs'] == 180:
                        invert_stab = 'true'
                if 'x' in key:
                    row_width += key['x']
            else:
                # row width is the offset
                ydelta = 19.05 / 2 - (19.05 * (nextheight-1)) / 2

                key_xpos = 19.05 * row_width
                key_width = nextkey * 19.05
                key_xpos += (key_width / 2) - 7

                key_ypos = (((max_rows - 1) - ridx) * 19.05) + (ydelta - 7)

                keys.append(('cherry1u',
                             key_xpos + key_xofs,
                             key_ypos + key_yofs))

                if nextheight == 2:
                    stabs.append(('%s_vertical' % stab_type,
                                  key_xpos + key_xofs,
                                  key_ypos + key_yofs,
                                  23.8, invert_stab))

                if nextkey >= 2 and nextkey <= 2.75:
                    stabs.append((stab_type,
                                  key_xpos + key_xofs,
                                  key_ypos + key_yofs,
                                  23.8, invert_stab))
                if nextkey == 6.25:
                    stabs.append((stab_type,
                                  key_xpos + key_xofs,
                                  key_ypos + key_yofs,
                                  100.0, invert_stab))

                row_width += nextkey
                nextkey = 1
                nextheight = 1
                invert_stab = 'false'

        widths.append(row_width)

    m_height = len(keydata)
    m_width = max(widths)

    if args.ptype == 'poker' and m_width > 15:
        print "too wide for poker"
        sys.exit(1)

    if args.ptype == 'tada' and m_width > 16:
        print "too wide for tada"
        sys.exit(1)

    if args.ptype == 'numpad' and (m_width > 4 or m_height > 5):
        print "too large for numpad"
        sys.exit(1)

    width = (19.05 * max(widths)) + extra_width

    # add screws
    if args.ptype == 'sandwich':
        if args.topscrews or args.sidescrews:
            drills.append((args.drillsize / 2,
                           1.5 * args.drillsize,
                           1.5 * args.drillsize))
            drills.append((args.drillsize / 2,
                           1.5 * args.drillsize,
                           height - (1.5 * args.drillsize)))
            drills.append((args.drillsize / 2,
                           width - (1.5 * args.drillsize),
                           1.5 * args.drillsize))
            drills.append((args.drillsize / 2,
                           width - (1.5 * args.drillsize),
                           height - (1.5 * args.drillsize)))
    elif args.ptype == 'poker':
        drill_width = args.drills / 2

        # sides
        drills.append((drill_width, width/2 - 139, height/2 - 9.2))
        drills.append((drill_width, width/2 + 139, height/2 - 9.2))

        # tab and pipe
        drills.append((drill_width, width/2 - 117.3, height/2 + 19.4))
        drills.append((drill_width, width/2 + 117.55, height/2 + 19.4))

        # g/h
        drills.append((drill_width, width/2 - 14.3, height/2 - 0))

        # space
        drills.append((drill_width, width/2 + 48, height/2 - 37.9))

        rects.append((1 + (width/2 - 139),
                      drill_width * 2,
                      -1,
                      height/2 - (9.2 + drill_width)))

        rects.append((1 + (width/2 - 139),
                      drill_width * 2,
                      width/2 + 139,
                      height/2 - (9.2 + drill_width)))
    elif args.ptype == 'tada':
        drill_width = args.drills / 2
        drills.append((drill_width, 25.575, 67.025))
        drills.append((drill_width, 25.575, 9.525))  # is this right?

        drills.append((drill_width, 128.575, 47.625))

        drills.append((drill_width, 187.6, 9.525))

        drills.append((drill_width, 260.425, 67.025))
        drills.append((drill_width, 266.70, 9.525))
    elif args.ptype == 'numpad':
        drill_width = args.drills / 2

        # These are the "old" positions for r1.0 boards.  They were dumb.
        # drills.append((drill_width, 19.05, 19.05))
        # drills.append((drill_width, 19.05 * 3, 19.05))
        # drills.append((drill_width, 19.05, 19.05 * 4))
        # drills.append((drill_width, 19.05 * 3, 19.05 * 4))

        drills.append((drill_width, 19.05, 19.05 * 1.5))
        drills.append((drill_width, 19.05 * 2.5, 19.05))
        drills.append((drill_width, 19.05, 19.05 * 4.5))
        drills.append((drill_width, 19.05 * 3, 19.05 * 4.5))

    printed_source = [json.dumps(x) for x in keydata]
    j2_kwargs = {'width': width,
                 'height': height,
                 'btrim': args.btrim,
                 'ttrim': args.ttrim,
                 'rtrim': args.rtrim,
                 'ltrim': args.ltrim,
                 'keys': keys,
                 'stabs': stabs,
                 'rects': rects,
                 'source': printed_source,
                 'cli': ' '.join(args.cli),
                 'dogbone': args.dogbone,
                 'widen': args.widen,
                 'drills': drills,
                 'rounded': args.rounded,
                 'rounded_toolsize': args.rounded_toolsize,
                 'tool_size': args.tool_size}

    basename = base_name(args.outfile, args.infile)
    template_file('plate.scad.j2', '%s.scad' % basename, j2_kwargs)


def get_parser():
    parser = argparse.ArgumentParser(description='Make a plate')

    parser.add_argument('infile', help='input file')
    parser.add_argument('--outfile',
                        help='output scad file (default based on infile)')
    parser.add_argument('--scad-only', action='store_true')
    parser.add_argument('--dogbone', help='make dogbones', action='store_true')
    parser.add_argument('--widen', help='widen', action='store_true')
    parser.add_argument('--tool-size', default=3.175,
                        type=float,
                        help='tool size in mm (1/4" = 6.35mm, 1/8" = 3.175mm)')
    parser.add_argument('--rounded', action='store_true')
    parser.add_argument(
        '--rounded-toolsize', default=6.35,
        type=float,
        help='fit inner corner made with tool of this size (default: 6.35)')
    parser.add_argument(
        '--stabs', choices=['cherry', 'open', 'small'],
        default='cherry',
        help='what kind of stabilizers')

    parser.add_argument(
        '--drills', default=6.35, type=float,
        help='diameter of drills for screw')

    parser.add_argument('--btrim', type=float, help='bottom trim', default=0.0)
    parser.add_argument('--ttrim', type=float, help='top trim', default=0.0)
    parser.add_argument('--rtrim', type=float, help='right trim', default=0.0)
    parser.add_argument('--ltrim', type=float, help='left trim', default=0.0)

    subparsers = parser.add_subparsers(help='plate type', dest='ptype')

    subparsers.add_parser('poker', help='poker 60%%')
    subparsers.add_parser('tada', help='tada 68%%')
    subparsers.add_parser('numpad', help='homegrown numpad case')

    sandwich_p = subparsers.add_parser('sandwich', help='sandwich case')
    sandwich_p.add_argument('--leftpadding', default=0, type=float)
    sandwich_p.add_argument('--rightpadding', default=0, type=float)
    sandwich_p.add_argument('--toppadding', default=0, type=float)
    sandwich_p.add_argument('--bottompadding', default=0, type=float)
    sandwich_p.add_argument('--drillsize', default=3.5, type=float)
    sandwich_p.add_argument('--topscrews', default=0)
    sandwich_p.add_argument('--sidescrews', default=0)

    return parser


def main(rawargs):
    args = get_parser().parse_args(rawargs)

    args.cli = sys.argv

    with open(args.infile, 'r') as f:
        j = json.loads(f.read())

    genscad(args, j)
    renderscad(args)

if __name__ == '__main__':
    main(sys.argv[1:])
