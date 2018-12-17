#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import os
import sys
import time
import traceback
import json
import struct
import base64
import binascii


#Global variables.  Don't judge me.
debug = False
inputfile = ""

AVIF_HASINDEX           = 0x00000010
AVIF_MUSTUSEINDEX       = 0x00000020
AVIF_ISINTERLEAVED      = 0x00000100
AVIF_TRUSTCKTYPE        = 0x00000800
AVIF_WASCAPTUREFILE     = 0x00010000
AVIF_COPYRIGHTED        = 0x00020000
AVI_MAX_RIFF_SIZE       = 0x4000000000000000
AVI_MASTER_INDEX_SIZE   = 256
AVIIF_INDEX             = 0x10

M5_AVI_IDX1_OFFSET      = 0x27000000

riff = dict()
offset = 0x00

__version__ = '1.0.0'




try:
    from argparse import ArgumentParser as ArgParser
except ImportError:
    from optparse import OptionParser as ArgParser
""" 
Repper file cmd line tool

Simple tool for executing the log_translator against an input file.

"""

def dashcamVideoParser():
    global riff,offset
    print("Dashcam Video Parser: {}".format(__version__))
    print("Reading file: {}".format(inputfile))
    avifile = open(inputfile, 'rb').read()
    if avifile:
        offset = 0
        (fourcc, fsize, ftype) = struct.unpack_from('4sI4s', avifile)
        riff['riff'] = fourcc.decode()
        riff['filesize'] = fsize
        riff['filesizehex'] = hex(fsize)
        riff['filetype'] = ftype.decode()
        offset = 0x0C
        while True:
            next_type = struct.unpack_from('4s', avifile, offset)[0]
            # print("next_type: ", next_type)
            offset = offset + 0x04
            # Get LIST
            if b'LIST' == next_type:
                (list_size, list_type)  = pullLIST(avifile)
                offset = offset+0x08
                # print ("type ", list_type, "; size ", list_size)
                if b'hdrl' == list_type:
                    avih = aviheader(avifile)
                    offset = offset+(0x04*16)
                    riff['hdrl'] = avih
                    # print(avih)

                if b'strl' == list_type:
                    strl = riff.get('strl')
                    if not strl:
                        strl = list()
                        riff['strl'] = strl
                    strl.append(pullstrl(avifile))

                if b'movi' == list_type:
                    movi = riff.get('movi')
                    if not movi:
                        movi = list()
                        riff['movi'] = movi
                    movi.append(pullmovi(avifile))

            elif b'JUNK' == next_type:
                junk_size = struct.unpack_from('I', avifile, offset)[0]
                offset = offset + 0x04
                # print("junk: ",junk_size)
                offset = offset + junk_size
            else:
                print("Not here: {}".format(pad_hex(hex(offset))))
                break

        # now go get the idx1 offset and loop through those, making a 
        # dictionary of offsets for the video

            
        # (name, lsize, ltype) = struct.unpack_from('4sI4s', avi, offset)
        print("-----")
        print(json.dumps(riff, indent=2))

def pullLIST(avifile):
    global offset
    return struct.unpack_from('I4s', avifile, offset)

def pullmovi(avifile):
    global offset
    res = list()
    count = 0
    while True:
        # fourcc = struct.unpack_from('4s', avifile, offset)[0]
        streamnumber = struct.unpack_from('2s', avifile, offset)[0]
        streamtype = struct.unpack_from('2s', avifile, offset+2)[0]
        print("Stream: {}; Type: {}".format(streamnumber,streamtype))
        if b'st' == streamtype:
            if b'02' == streamnumber:
                # print('02st')
                st02 = dict()                    
                st02['offset'] = pad_hex(hex(offset))
                (fcc, ssize, unk1, unk2) = struct.unpack_from('4s3I', avifile, offset)
                print(fcc, " ", ssize, " ", unk1, " ", unk2)
                offset = offset + (4*0x04)
                gpsstr_fmt = '{}sI'.format(unk2-0x04)
                (gpsstr, unk3) = struct.unpack_from(gpsstr_fmt, avifile, offset)
                offset = offset + unk2
                st02['fourcc'] = fcc.decode()
                st02['structsize'] = ssize
                st02['unk1'] = unk1
                st02['unk2'] = unk2
                st02['gps'] = gpsstr.decode()
                st02['unk3'] = unk3
                res.append(st02)
            elif b'03' == streamnumber:
                # print('03st')
                st03 = dict()
                st03['offset'] = pad_hex(hex(offset))
                (fcc, ssize, unk1, unk2, unk3) = struct.unpack_from('4s4I', avifile, offset)
                offset = offset + (5*0x04)
                st03['fourcc'] = fcc.decode()
                st03['structsize'] = ssize
                st03['unk1'] = unk1
                st03['unk2'] = unk2
                st03['unk3'] = unk3
                res.append(st03)
            else:
                print("Unknown st")
        elif b'dc' == streamtype:
            # print ('00dc')
            dc = dict()
            dc['offset'] = pad_hex(hex(offset))
            (fcc, ssize) = struct.unpack_from('4sI', avifile, offset)
            dc['fourcc'] = fcc.decode()
            dc['structsize'] = ssize
            offset = offset + 0x08
            data_fmt = '{}s'.format(ssize)

            filename = "test-{}-{}.mov".format(str(streamnumber), str(streamtype))
            filebytes = bytearray(struct.unpack_from(data_fmt, avifile, offset)[0])
            aviout = open(filename, 'wb')
            aviout.write(filebytes)
            aviout.close() 
            # print (data_fmt)
            #b64data = binascii.b2a_base64(struct.unpack_from(data_fmt, avifile, offset)[0])
            # print(b64data)
            # dc['data'] = b64data.decode()
            offset = offset + ssize
            res.append(dc)
        elif b'wb' == streamtype:
            # print('01wb')
            wb01 = dict()
            wb01['offset'] = pad_hex(hex(offset))
            (fcc, ssize) = struct.unpack_from('4sI', avifile, offset)
            wb01['fourcc'] = fcc.decode()
            wb01['structsize'] = ssize
            offset = offset + 0x08
            data_fmt = '{}s'.format(ssize)
            print (data_fmt)
            b64data = binascii.b2a_base64(struct.unpack_from(data_fmt, avifile, offset)[0])
            # print (b64data)
            # wb01['data'] = b64data.decode()
            offset = offset+ssize
            res.append(wb01)
        else:
            break
    return res

def pullstrl(avifile):
    global offset
    stream_type = None
    res = dict()
    while True:
        fourcc = struct.unpack_from('4s', avifile, offset)[0]
        # print("start: ", fourcc)
        if b'strh' == fourcc:
            (fcc, structsize, fcctype, fcchandler, flags, priority, language, initialFrames, \
            scale, rate, start, length, suggestedBufferSize, quality, sampleSize, \
            frame_left, frame_top, frame_right, frame_bottom) \
            = struct.unpack_from('4sI4s4sI2H8I4H', avifile, offset)
            strh = dict()
            strh['offset'] = pad_hex(hex(offset))
            strh['size'] = structsize
            stream_type = fcctype.decode()
            strh['type'] = stream_type
            strh['handler'] = fcchandler.decode()
            strh['flags'] = flags
            strh['priority'] = priority
            strh['language'] = language
            strh['initial_frames'] = initialFrames
            strh['scale'] = scale
            strh['rate'] = rate
            strh['start'] = start
            strh['length'] = length
            strh['suggest_buffer_size'] = suggestedBufferSize
            strh['quality'] = quality
            strh['sample_size'] = sampleSize
            strh['frame'] = dict()
            strh['frame']['left'] = frame_left
            strh['frame']['top'] = frame_top
            strh['frame']['right'] = frame_right
            strh['frame']['bottom'] = frame_bottom
            res['strh'] = strh
            offset = offset + (16*0x04)
        elif b'strf' == fourcc:
            strf = list()
            # print("stream type: ", stream_type)
            if 'vids' == stream_type:
                vid = dict()
                vid['offset'] = pad_hex(hex(offset))
                (fcc, ssize, bsize, width, height, planes, bitcount, compression, sizeImage, \
                xpels, ypels, clrused, clrimp) = struct.unpack_from('4s4I2H4s5I',avifile, offset)
                vid['structsize'] = ssize
                vid['size'] = bsize
                vid['width'] = width
                vid['height'] = height
                vid['planes'] = planes
                vid['bitcount'] = bitcount
                vid['compression'] = compression.decode()
                vid['size_image'] = sizeImage
                vid['xpels'] = xpels
                vid['ypels'] = ypels
                vid['clrused'] = clrused
                vid['clrimp'] = clrimp
                strf.append(vid)
                offset = offset + (12*0x04)
            elif 'auds' == stream_type:
                aud = dict()
                aud['offset'] = pad_hex(hex(offset))
                (fcc, ssize, formatTag, channels, samplesPerSec, avgBytesPerSec, \
                blockAlign, bitsPerSample, bsize) = struct.unpack_from('4sI2H2I2HI',avifile, offset)
                aud['structsize'] = ssize
                aud['format_tag'] = formatTag
                aud['channels'] = channels
                aud['samples_per_sec'] = samplesPerSec
                aud['avg_bytes_per_sec'] = avgBytesPerSec
                aud['block_align'] = blockAlign
                aud['bits_per_sample'] = bitsPerSample
                aud['size'] = bsize
                strf.append(aud)
                offset = offset + (7*0x04)
            elif 'txts' == stream_type:
                (fcc, ssize, one, two, three, four, five) \
                = struct.unpack_from('4s6I', avifile, offset)
                txt = dict()
                txt['offset'] = pad_hex(hex(offset))
                txt['structsize'] = ssize
                txt['one'] = one
                txt['two'] = two
                txt['three'] = three
                txt['four'] = four
                txt['five'] = five
                strf.append(txt)
                offset = offset + (7*0x04)
            else:
                break
            res['strf'] = strf
        else:
            break

    return res


def aviheader(avifile):
    global offset
    (fourcc, cb, microSecPerFrame, maxBytesPerSec, \
    paddingGranularity, flags, totalFrames, \
    initialFrames, streams, suggestedBufferSize, \
    width, height, reserved0, reserved1, reserved2, reserved3) = \
    struct.unpack_from('4s15I', avifile, offset)
    avih = dict()
    avih['offset'] = pad_hex(hex(offset))
    avih['key'] = fourcc.decode()
    avih['sizeofstruct'] = cb
    avih['microsec_between_frames'] = microSecPerFrame
    avih['maximum_data_rate'] = maxBytesPerSec
    avih['paddding'] = paddingGranularity
    avih['flags'] = dict()
    avih['flags']['copyrighted'] = False if (flags & AVIF_COPYRIGHTED) == 0 else True
    avih['flags']['hasindex'] = False if (flags & AVIF_HASINDEX) == 0 else True
    avih['flags']['isinterleaved'] = False if (flags & AVIF_ISINTERLEAVED) == 0 else True
    avih['flags']['mustuseindex'] = False if (flags & AVIF_MUSTUSEINDEX) == 0 else True
    avih['flags']['wascapturefile'] = False if (flags & AVIF_WASCAPTUREFILE) == 0 else True
    avih['total_frames'] = totalFrames
    avih['initial_frames'] = initialFrames
    avih['streams'] = streams
    avih['suggested_buffer_size'] = suggestedBufferSize
    avih['width'] = width
    avih['height'] = height
    avih['reserved0'] = reserved0
    avih['reserved1'] = reserved1
    avih['reserved2'] = reserved2
    avih['reserved3'] = reserved3
    return avih


def pad_hex(hexstr, fillsz=8):
    return '0x' + hexstr[2:].zfill(fillsz)


def version():
    print (os.path.basename(__file__), ":", __version__)
    raise SystemExit()


def parserArgs():
    global debug, inputfile
    description = (
            'Script for parsing Momento 5 dashcam video\n'
            '------------------------------------------\n'
            )
    parser = ArgParser(description=description)
    # If we're using optparse.OptionParser, creat 'add_argument' method
    # for argparse.ArgumentParser compatibility
    try:
        parser.add_argument = parser.add_option
    except AttributeError:
        pass

    parser.add_argument('-v', '--version', action='store_true', help='Show version numbers and exit')
    parser.add_argument('-i', '--inputfile', help='Specify the file to scan', default=inputfile)
    parser.add_argument('-d', '--debug', action='store_true', help='Prints extra stuff to stdout')
    
    options = parser.parse_args()
    if isinstance(options, tuple):
        args = options[0]
    else:
        args = options
    del options

    if args.version:
        version()
    
    if args.debug:
        debug = args.debug

    if args.inputfile:
        inputfile = args.inputfile
    else:
        inputfile = None

    should_exit = False
    if inputfile is None or inputfile == '':
        print("The inputfile cannot be empty")
        should_exit = True

    if should_exit == True:
        raise SystemExit()


def main():
    parserArgs()
    try:
        dashcamVideoParser()
    except KeyboardInterrupt:
        print("\nCancelling...\n")
    except Exception as ex:
        #If retry, let's try this again...
        traceback.print_exc()
        print ("\nCaught Exception: {}".format(ex))


if __name__ == '__main__':
    main()