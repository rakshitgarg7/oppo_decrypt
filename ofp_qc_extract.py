#!/usr/bin/env python3
# (c) B.Kerler, MIT license
import os
import sys
import xml.etree.ElementTree as ET
from struct import unpack
from binascii import unhexlify, hexlify
from Crypto.Cipher import AES
from Crypto.Hash import MD5
import hashlib
import shutil

def swap(ch):
    return ((ch & 0xF) << 4) + ((ch & 0xF0) >> 4)


def keyshuffle(key, hkey):
    for i in range(0, 0x10, 4):
        key[i] = swap((hkey[i] ^ key[i]))
        key[i + 1] = swap(hkey[i + 1] ^ key[i + 1])
        key[i + 2] = swap(hkey[i + 2] ^ key[i + 2])
        key[i + 3] = swap(hkey[i + 3] ^ key[i + 3])
    return key

def ROR(x, n, bits = 32):
    mask = (2**n) - 1
    mask_bits = x & mask
    return (x >> n) | (mask_bits << (bits - n))

def ROL(x, n, bits = 32):
    return ROR(x, bits - n, bits)

def generatekey1():
    key1 = "42F2D5399137E2B2813CD8ECDF2F4D72"
    key2 = "F6C50203515A2CE7D8C3E1F938B7E94C"
    key3 = "67657963787565E837D226B69A495D21"

    key1 = bytearray.fromhex(key1)
    key2 = bytearray.fromhex(key2)
    key3 = bytearray.fromhex(key3)

    key2 = keyshuffle(key2, key3)
    aeskey = bytes(hashlib.md5(key2).hexdigest()[0:16], 'utf-8')
    key1 = keyshuffle(key1, key3)
    iv = bytes(hashlib.md5(key1).hexdigest()[0:16], 'utf-8')
    return aeskey,iv

def generatekey2(filename):
    keys = [
                #R9s/A57t
                ["V1.4.17/1.4.27",                          "27827963787265EF89D126B69A495A21","82C50203285A2CE7D8C3E198383CE94C","422DD5399181E223813CD8ECDF2E4D72"],
                ["V1.5.13",                                 "67657963787565E837D226B69A495D21","F6C50203515A2CE7D8C3E1F938B7E94C","42F2D5399137E2B2813CD8ECDF2F4D72"],
                #R15 Pro CPH1831 V1.6.6 / FindX CPH1871 V1.6.9 / R17 Pro CPH1877 V1.6.17 / R17 PBEM00 V1.6.17 / A5 2020 V1.7.6 / K3 CPH1955 V1.6.26 UFS
                #Reno 5G CPH1921 V1.6.26 / Realme 3 Pro RMX1851 V1.6.17 / Reno 10X Zoom V1.6.26 / R17 CPH1879 V1.6.17 / R17 Neo CPH1893 / K1 PBCM30
                ["V1.6.6/1.6.9/1.6.17/1.6.24/1.6.26/1.7.6", "3C2D518D9BF2E4279DC758CD535147C3","87C74A29709AC1BF2382276C4E8DF232","598D92E967265E9BCABE2469FE4A915E"],
                #a3s
                ["V1.6.17",                                 "E11AA7BB558A436A8375FD15DDD4651F","77DDF6A0696841F6B74782C097835169","A739742384A44E8BA45207AD5C3700EA"],
                #RM1921EX V1.7.2, Realme X RMX1901 V1.7.2, Realme 5 Pro RMX1971 V1.7.2, Realme 5 RMX1911 V1.7.2
                ["V1.7.2",                                  "8FB8FB261930260BE945B841AEFA9FD4","E529E82B28F5A2F8831D860AE39E425D","8A09DA60ED36F125D64709973372C1CF"]
    ]

    for dkey in keys:
        key = bytearray()
        iv = bytearray()
        # "Read metadata failed"
        mc = bytearray.fromhex(dkey[1])
        userkey=bytearray.fromhex(dkey[2])
        ivec=bytearray.fromhex(dkey[3])

        #userkey=bytearray(unhexlify("A3D8D358E42F5A9E931DD3917D9A3218"))
        #ivec=bytearray(unhexlify("386935399137416B67416BECF22F519A"))
        #mc=bytearray(unhexlify("9E4F32639D21357D37D226B69A495D21"))

        for i in range(0,len(userkey)):
            v=ROL((userkey[i]^mc[i]),4,8)
            key.append(v)

        for i in range(0,len(userkey)):
            v=ROL((ivec[i]^mc[i]),4,8)
            iv.append(v)

        h=MD5.new()
        h.update(key)
        key=h.digest()

        h = MD5.new()
        h.update(iv)
        iv = h.digest()

        key=hexlify(key).lower()[0:16]
        iv=hexlify(iv).lower()[0:16]
        pagesize,data=extract_xml(filename,key,iv)
        if pagesize!=0:
            return pagesize,key,iv,data
    return 0,None,None,None


def extract_xml(filename,key,iv):
    filesize=os.stat(filename).st_size
    with open(filename,'rb') as rf:
        pagesize = 0x200
        xmloffset=filesize-pagesize
        rf.seek(xmloffset+0x10)
        if unpack("<I",rf.read(4))[0]==0x7CEF:
            pagesize=0x200
        else:
            pagesize=0x1000
            xmloffset=filesize-pagesize
            rf.seek(xmloffset + 0x10)
            magic=unpack("<I", rf.read(4))[0]
            if not magic == 0x7CEF:
                print("Unknown pagesize. Aborting")
                exit(0)

        rf.seek(xmloffset+0x14)
        offset=unpack("<I",rf.read(4))[0]*pagesize
        length=unpack("<I",rf.read(4))[0]
        if length<200: #A57 hack
            length=xmloffset-offset-0x57
        rf.seek(offset)
        data=rf.read(length)
        dec=aes_cfb(data,key,iv)

        #h=MD5.new()
        #h.update(data)
        #print(dec.decode('utf-8'))
        #print(h.hexdigest())
        #print("Done.")
        if b"<?xml" in dec:
            return pagesize,dec
        else:
            return 0,""

def aes_cfb(data,key,iv):
    ctx = AES.new(key, AES.MODE_CFB, iv=iv, segment_size=128)
    decrypted = ctx.decrypt(data)
    return decrypted

def copysub(rf,wf,start,length):
    rf.seek(start)
    rlen=0
    while (length > 0):
        if length < 0x100000:
            size = length
        else:
            size = 0x100000
        data = rf.read(size)
        wf.write(data)
        rlen+=len(data)
        length -= size
    return rlen

def decryptfile(key,iv,filename,path,wfilename,start,length,rlength,decryptsize=0x40000):
    print(f"Extracting {wfilename}")
    if rlength==length:
        length=(length//0x4*0x4)

    with open(filename, 'rb') as rf:
        with open(os.path.join(path, wfilename), 'wb') as wf:
            rf.seek(start)
            if length>decryptsize:
                size=decryptsize
            else:
                size=length
            data=rf.read(size)
            if size%4:
                data+=(4-(size%4))*b'\x00'
            outp = aes_cfb(data, key, iv)
            if size==decryptsize:
                wf.write(outp[:size])
                rlength-=size
                if rlength>0:
                    copysub(rf,wf,start+decryptsize,rlength)
            else:
                wf.write(outp[:rlength])

def main():
    if len(sys.argv)<3:
        print("Usage: ./ofp_qc_extract.py [Filename.ofp] [Directory to extract files to]")
        exit(0)

    filename=sys.argv[1]
    outdir=sys.argv[2]
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    #key,iv=generatekey1()
    pagesize,key,iv,data=generatekey2(filename)
    if pagesize==0:
        print("Unknown key. Aborting")
        exit(0)
    else:
        xml=data[:data.rfind(b">")+1].decode('utf-8')

    if "/" in filename:
        path = filename[:filename.rfind("/")]
    elif "\\" in filename:
        path = filename[:filename.rfind("\\")]
    else:
        path = ""

    path = os.path.join(path,outdir)

    if os.path.exists(path):
        shutil.rmtree(path)
        os.mkdir(path)
    else:
        os.mkdir(path)

    root = ET.fromstring(xml)
    for child in root:
        if child.tag == "Sahara":
            for item in child:
                if item.tag == "File":
                    wfilename = item.attrib["Path"]
                    start = int(item.attrib["FileOffsetInSrc"]) * pagesize
                    length = int(item.attrib["SizeInSectorInSrc"]) * pagesize
                    rlength = int(item.attrib["SizeInByteInSrc"])
                    decryptfile(key, iv, filename, path, wfilename, start, length, rlength,rlength)
        elif child.tag in ["Config","Provision","ChainedTableOfDigests","DigestsToSign"]:
            for item in child:
                if item.tag == "config":
                    wfilename = item.attrib["filename"]
                    if "SizeInSectorInSrc" in item.attrib:
                        start = int(item.attrib["SizeInSectorInSrc"]) * pagesize
                    else:
                        continue
                    length = int(item.attrib["SizeInByteInSrc"])
                    decryptfile(key,iv,filename, path, wfilename, start, length,length)
        elif child.tag in ["AllFile","Data","Data1","Data2"]:
            # if not os.path.exists(os.path.join(path, child.tag)):
            #    os.mkdir(os.path.join(path, child.tag))
            # spath = os.path.join(path, child.tag)
            for item in child:
                if "filename" in item.attrib:
                    wfilename = item.attrib["filename"]
                    if wfilename == "":
                        continue
                    start = int(item.attrib["FileOffsetInSrc"])
                    rlength = int(item.attrib["SizeInByteInSrc"])
                    if "SizeInSectorInSrc" in item.attrib:
                        length = int(item.attrib["SizeInSectorInSrc"]) * pagesize
                    else:
                        length=rlength
                    decryptfile(key,iv,filename, path, wfilename, start, length,rlength)
        elif "Program" in child.tag:
            # if not os.path.exists(os.path.join(path, child.tag)):
            #    os.mkdir(os.path.join(path, child.tag))
            # spath = os.path.join(path, child.tag)
            for item in child:
                if "filename" in item.attrib:
                    wfilename = item.attrib["filename"]
                    if wfilename == "":
                        continue
                    start = int(item.attrib["FileOffsetInSrc"]) * pagesize
                    rlength = int(item.attrib["SizeInByteInSrc"])
                    if "SizeInSectorInSrc" in item.attrib:
                        length = int(item.attrib["SizeInSectorInSrc"]) * pagesize
                    else:
                        length=rlength
                    decryptfile(key,iv,filename, path, wfilename, start, length,rlength)
                else:
                    for subitem in item:
                        if "filename" in subitem.attrib:
                            wfilename = subitem.attrib["filename"]
                            if wfilename == "":
                                continue
                            start = int(subitem.attrib["FileOffsetInSrc"]) * pagesize
                            length = int(subitem.attrib["SizeInSectorInSrc"]) * pagesize
                            rlength = int(item.attrib["SizeInByteInSrc"])
                            decryptfile(key,iv,filename, path, wfilename, start, length,rlength)
        # else:
        #    print (child.tag, child.attrib)
    print("Done. Extracted files to " + path)
    exit(0)


if __name__=="__main__":
    main()
