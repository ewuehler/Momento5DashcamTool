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

# The files are a fixed file size and the movi indexes
# are all found here.  Parsing the file stream will eventually
# cause errors as there will be "leftover" data from a previous
# memory location...
M5_EVT2_IDX1_OFFSET     = 0x02700000
M5_IMP2_IDX1_OFFSET     = 0x02700000
M5_MOT2_IDX1_OFFSET     = 0x02700000
M5_REC2_IDX1_OFFSET     = 0x04F00000

riff = dict()
offset = 0x00

__version__ = '1.0.0'


try:
    from argparse import ArgumentParser as ArgParser
except ImportError:
    from optparse import OptionParser as ArgParser


def dashcamVideoParser():
    global riff,offset
    # print("Momento 5 Dashcam Video Parser: {}".format(__version__))
    # print("Reading file: {}".format(inputfile))
    filename = os.path.basename(inputfile)
    if filename.startswith('REC2'):
        idx1offset = M5_REC2_IDX1_OFFSET
    elif filename.startswith('MOT2'):
        idx1offset = M5_MOT2_IDX1_OFFSET  
    elif filename.startswith('IMP2'):
        idx1offset = M5_IMP2_IDX1_OFFSET  
    elif filename.startswith('EVT2'):
        idx1offset = M5_EVT2_IDX1_OFFSET  
    else:
        idx1offset = M5_EVT2_IDX1_OFFSET  
    avifile = open(inputfile, 'rb').read()
    if avifile:
        # first up, scan the file and get the movi offsets
        movioffsets = generateMoviOffsets(avifile, idx1offset)
        offset = 0
        (fourcc, fsize, ftype) = struct.unpack_from('4sI4s', avifile)
        riff['riff'] = fourcc.decode()
        riff['filesize'] = fsize
        riff['filesizehex'] = pad_hex(hex(fsize))
        riff['filetype'] = ftype.decode()
        offset = 0x0C
        while True:
            next_type = struct.unpack_from('4s', avifile, offset)[0]
            # print("next_type: ", next_type)
            offset = offset + 0x04
            # Get LIST
            if b'LIST' == next_type:
                (list_size, list_type) = pullLIST(avifile)
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
#                    movi.append(movioffsets)
                    movi.append(pullmovi(avifile, movioffsets,offset))

            elif b'JUNK' == next_type:
                junk_size = struct.unpack_from('I', avifile, offset)[0]
                offset = offset + 0x04
                # TODO: there is something in the JUNK - the fact that it has the file name
                # implies to me anyway that the data in "JUNK" probably solves some problems
                # elsewhere in the parsing.  Hooray for proprietary bits!
                fname = struct.unpack_from('28s',avifile,offset)[0]
                riff['filename'] = fname.decode().rstrip(' \t\r\n\0')
                offset = offset + junk_size
            else:
                # print("Parsing Complete")
                break

        # now go get the idx1 offset and loop through those, making a 
        # dictionary of offsets for the video

            
        # (name, lsize, ltype) = struct.unpack_from('4sI4s', avi, offset)
        # print("-----")
        print(json.dumps(riff, indent=2))

def pullLIST(avifile):
    global offset
    return struct.unpack_from('I4s', avifile, offset)

def pullmovi(avifile, movioffsets, initialoffset):
    res = list()
    knowntypes = ['st', 'dc', 'db', 'wb', 'pc']
    for (fourcc, flag, moffset, length) in movioffsets:
        moffset = moffset + initialoffset
        # streamnumber = struct.unpack_from('2s', avifile, moffset)[0]
        # streamtype = struct.unpack_from('2s', avifile, moffset+2)[0]
        streamnumber = fourcc[:2]
        streamtype = fourcc[2:]
        # print("Stream: {}; Type: {}; Offset: {}; Offset Hex: {}".format(streamnumber,streamtype, moffset, pad_hex(hex(moffset))))

        if streamtype in knowntypes:
            sd = dict()
            sd['fourcc'] = fourcc
            sd['offset'] = moffset
            sd['offsethex'] = pad_hex(hex(moffset))
            ssize = struct.unpack_from('I', avifile, moffset)[0]
            # sd['structsize'] = ssize
            moffset = moffset + 0x04
            sdd = dict()
            sdd['offset'] = moffset
            sdd['offsethex'] = pad_hex(hex(moffset))
            sdd['datasize'] = ssize
            
            # TODO: Figure out how/why I would want to pull the data from the streams
            # and put it together...  For now just dump the stream data.
            if 'st' == streamtype:  ## Non-standard stream type
                if '03' == streamnumber:
                    (flags, size) = struct.unpack_from('2I', avifile,moffset)
                    unpackbits = '{}s'.format(size)
                    content = struct.unpack_from(unpackbits, avifile, moffset+0x08)[0]
                    sdd['flags'] = flags
                    sdd['size'] = size
                    sdd['gps'] = content.decode().rstrip(' \t\r\n\0')
                elif '04' == streamnumber:
                    sdd['todo'] = '<{} bytes of data>'.format(ssize)
                else:
                    sdd['todo'] = '<{} bytes of data from unknown stream number>'.format(ssize)
            elif 'dc' == streamtype:  ## Compressed Video Frame
                sdd['todo'] = '<{} bytes of data>'.format(ssize)
                # data_fmt = '{}s'.format(ssize)
                #b64data = binascii.b2a_base64(struct.unpack_from(data_fmt, avifile, offset)[0])
                # dc['data'] = b64data.decode()
                pass
            elif 'db' == streamtype: ## Uncompressed Video Frame
                sdd['todo'] = '<{} bytes of data>'.format(ssize)
                # data_fmt = '{}s'.format(ssize)
                #b64data = binascii.b2a_base64(struct.unpack_from(data_fmt, avifile, offset)[0])
                # dc['data'] = b64data.decode()
                pass
            elif 'wb' == streamtype: ## Audio data
                sdd['todo'] = '<{} bytes of data>'.format(ssize)
                # data_fmt = '{}s'.format(ssize)
                # print (data_fmt)
                # b64data = binascii.b2a_base64(struct.unpack_from(data_fmt, avifile, offset)[0])
                # print (b64data)
                pass 
            elif 'pc' == streamtype:  ## Palette change
                sdd['todo'] = '<{} bytes of data>'.format(ssize)
                pass
            #moffset = moffset + ssize
            sd['data'] = sdd
            res.append(sd)
        else:
            print("Unknown Stream: {}; Type: {}; Offset: {}; Offset Hex: {}".format(streamnumber,streamtype, moffset, pad_hex(hex(moffset))))
            # Need to figure out how to calculate the last blob of data in these streams as 
            # the type is not correct...
            #sys.exit()
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

# Since it appears the individual AVI files are not created from clean
# memory (previous files in memory leave bogus data in current files),
# it appears we need to use the idx1 list so we don't get lost in bad
# data...
def generateMoviOffsets(avifile, idx1offset):
    idx1 = list()
    # print("offset: {} ({})".format(idx1offset, pad_hex(hex(idx1offset))))
    (fourcc, ssize) = struct.unpack_from('4sI', avifile, idx1offset)
    if (fourcc.decode() == 'idx1'):
        # print("Index Offset: {}; Size: {}".format(fourcc.decode(), int(ssize)))
        idxoff = idx1offset + 0x08
        while True:
            (fcc, flags, moffset, msize) = struct.unpack_from('4s3I', avifile,idxoff)
            # print("chunk: {}; flags: {}; offset: {}; size: {}".format(fcc.decode(), flags, moffset, msize))
            idx1.append([fcc.decode(),int(flags),int(moffset),int(msize)])
            idxoff = idxoff + 0x10
            if idxoff >= idx1offset+0x08+ssize:
                break
    return idx1



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