#!/usr/bin/env python

import argparse
import json
import os
import sys

import jinja2


def template_file(infile, outfile, kwargs):
    path, filename = os.path.split(infile)
    j2_env = jinja2.Environment(loader=jinja2.FileSystemLoader(path) or '.')
    result = j2_env.get_template(filename).render(**kwargs)

    with open(outfile, 'w') as f:
        f.write(result)


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
        invert_stab = 'false'

        for key in row:
            if isinstance(key, dict):
                if 'w' in key:
                    nextkey = key['w']
                if '_rs' in key:
                    if key['_rs'] == 180:
                        invert_stab = 'true'
            else:
                # row width is the offset
                key_xpos = 19.05 * row_width
                key_width = nextkey * 19.05
                key_xpos += (key_width / 2) - 7

                key_ypos = (((max_rows - 1) - ridx) * 19.05) + ((19.05 / 2) - 7)

                keys.append(('cherry1u',
                             key_xpos + key_xofs,
                             key_ypos + key_yofs))

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
                invert_stab = 'false'

        widths.append(row_width)

    if args.ptype == 'poker' and max(widths) > 15:
        print "too wide for poker"
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

    else:  # poker
        drill_width = 6.35/2

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

    printed_source = [json.dumps(x) for x in keydata]
    j2_kwargs = {'width': width,
                 'height': height,
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

    outfile = args.outfile
    if not outfile:
        outfile = '.'.join(os.path.basename(
            os.path.abspath(args.infile)).split('.')[:-1])
        outfile += '-plate'

    template_file('plate.scad.j2', '%s.scad' % outfile, j2_kwargs)


def get_parser():
    parser = argparse.ArgumentParser(description='Make a plate')

    parser.add_argument('infile', help='input file')
    parser.add_argument('--outfile',
                        help='output scad file (default based on infile)')
    parser.add_argument('--dogbone', help='make dogbones', action='store_true')
    parser.add_argument('--widen', help='widen', action='store_true')
    parser.add_argument('--tool-size', default=3.175,
                        type=float,
                        help='tool size in mm (1/4" = 6.35mm, 1/8" = 3.175mm)')
    parser.add_argument('--rounded', action='store_true')
    parser.add_argument(
        '--rounded-toolsize', default=6.35,
        type=float,
        help='fit inner corner made with tool of this size (mm)')
    parser.add_argument(
        '--stabs', choices=['cherry', 'open'],
        default='cherry',
        help='what kind of stabilizers')

    subparsers = parser.add_subparsers(help='plate type', dest='ptype')

    poker_p = subparsers.add_parser('poker', help='poker 60%%')

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


if __name__ == '__main__':
    main(sys.argv[1:])
