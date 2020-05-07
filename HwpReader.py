import struct
import zlib
from io import BytesIO
import re
import olefile
import argparse

class char(object):
    size = 1
class inline(object):
    size = 8
class extended(object):
    size = 8

control_char_table = {
    0x00: ('UNUSABLE', char),
    0x01: ('RESERVED0', extended),
    0x02: ('SECTION_OR_COLUMN_DEF', extended),
    0x03: ('FIELD_START', extended),
    0x04: ('FIELD_END', inline),
    0x05: ('RESERVED1', inline),
    0x06: ('RESERVED2', inline),
    0x07: ('RESERVED3', inline),
    0x08: ('TITLE_MARK', inline),
    0x09: ('TAB', inline),
    0x0a: ('LINE_BREAK', char),
    0x0b: ('DRAWING_OR_TABLE', extended),
    0x0c: ('RESERVED4', extended),
    0x0d: ('PARA_BREAK', char),
    0x0e: ('RESERVED5', extended),
    0x0f: ('HIDDEN_EXPLANATION', extended),
    0x10: ('HEADER_OR_FOOTER', extended),
    0x11: ('FOOTNOTE_OR_ENDNOTE', extended),
    0x12: ('AUTO_NUMBERING', extended),
    0x13: ('RESERVED6', inline),
    0x14: ('RESERVED7', inline),
    0x15: ('PAGE_CONTROL', extended),
    0x16: ('BOOKMARK', extended),
    0x17: ('DUTMAL_OR_CHAR_OVERLAP', extended),
    0x18: ('HYPEN', char),
    0x19: ('RESERVED8', char),
    0x1a: ('RESERVED9', char),
    0x1b: ('RESERVED10', char),
    0x1c: ('RESERVED11', char),
    0x1d: ('RESERVED12', char),
    0x1e: ('NONBREAK_SPACE', char),
    0x1f: ('FIXEDWIDTH_SPACE', char),
}

class HwpReader(object):
    def __init__(self, filePath, fileName):
        self._ole = olefile.OleFileIO(filePath + fileName)
    
    @property
    def headerList(self):
        self.__headerList = self._ole.listdir()
        return self.__headerList

    @property
    def sectionList(self):
        self.__sectionList = []
        for header in self.headerList:
            if len(header) == 0:
                continue
            else:
                if header[0] == 'BodyText':
                    self.__sectionList.append( header[0] + '/' + header[1])
        return self.__sectionList

    def stream2txt(self, section):
        stream = self._ole.openstream(section)
        stream = BytesIO(zlib.decompress(stream.read(), -15))

        plain_txt = ''

        while True:
            header = stream.read(4)
            if not header:
                break
            header = struct.unpack('<I', header)[0]
            tag_id = header & 0x3ff
            level = (header >> 10) & 0x3ff
            size = (header >> 20) & 0xfff

            if size == 0xfff:
                size = struct.unpack('<I', stream.read(4))[0]
            
            payload = stream.read(size)
            regex = re.compile(rb'([\x00-\x1f])\x00')

            text = ''
            cursor_idx = 0
            search_idx = 0

            while cursor_idx < len(payload):
                if search_idx < cursor_idx:
                    search_idx = cursor_idx

                searched = regex.search(payload, search_idx)
                if searched:
                    pos = searched.start()

                    if pos & 1:
                        search_idx = pos + 1
                    elif pos > cursor_idx:
                        if tag_id == 67:
                            text += payload[cursor_idx:pos].decode('utf-16')
                        cursor_idx = pos
                    else:
                        control_char = ord(searched.group(1))
                        control_char_size = control_char_table[control_char][1].size

                        if control_char == '0x0a':
                            text += '\n'
                        cursor_idx = pos + control_char_size * 2
                else:
                    if tag_id == 67:
                        text += payload[search_idx:].decode('utf-16')
                    break
            if tag_id == 67:
                plain_txt += text + "\n"
        return plain_txt

    @property
    def hwp2txt(self):
        self.__hwp2txt = ''
        for section in self.sectionList:
            self.__hwp2txt += self.stream2txt(section)
        return self.__hwp2txt

    def writeFile(self, filePath, fileName):
        f = open(filePath + fileName , mode = 'wt', encoding = "utf-16")
        f.write(self.hwp2txt)
        f.close()

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('inputPath', type=str, help = "the input base path", default="./")
    parser.add_argument('inputFile', type=str, help = "the input base file name")
    parser.add_argument('outputPath', type=str, help = "the output base path", default="./")
    parser.add_argument('outputFile', type=str, help = "the output base file name", default="output")

    args = parser.parse_args()

    hwpReader = HwpReader(args.inputPath, args.inputFile)
    hwpReader.writeFile(args.outputPath, args.outputFile)