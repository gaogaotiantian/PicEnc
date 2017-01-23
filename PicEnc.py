from PIL import Image
import subprocess
import random
import argparse
import os

class Key:
    def __init__(self, cubeSize = 8, rollRound = 2):
        self.cubeSize = cubeSize
        self.rollRound = rollRound
        self.value = []
        self.curIndex = 0
    def GenKey(self, num):
        self.value = []
        for i in range(num):
            self.value.append(random.randrange(0, 65536))
        self.curIndex = 0
    def PrepareEnc(self):
        self.curIndex = 0
    def GetEncKey(self):
        retVal = self.value[self.curIndex]
        self.curIndex = (self.curIndex + 1) % len(self.value)
        return retVal
    def PrepareDec(self, num):
        self.curIndex = (num*self.rollRound-1) % len(self.value)
    def GetDecKey(self):
        retVal = self.value[self.curIndex]
        self.curIndex = (self.curIndex - 1) % len(self.value)
        return retVal
    def SaveKey(self, filename = 'key'):
        with open(filename, 'wb') as f:
            data = []
            data.append(self.cubeSize)
            data.append(self.rollRound)
            for val in self.value:
                data.append(int(val/256))
                data.append(val % 256)
            f.write(bytearray(data))
    def LoadKey(self, filename = 'key'):
        self.value = []
        self.curIndex = 0
        with open(filename, 'rb') as f:
            b = f.read(1)
            self.cubeSize = ord(b)
            b = f.read(1)
            self.rollRound = ord(b)
            ba = bytearray(f.read())
            for i in range(0, len(ba)-1, 2):
                b1 = ba[i]
                b2 = ba[i+1]
                self.value.append(b1*256+b2)
        return self
class Cube:
    def __init__(self, path = None):
        self.im = None
        self.width = None
        self.height = None
        self.cubeWidth = None
        self.cubeHeight = None
        self.cubeSize = 8 
        if path != None:
            self.path = path
            self.LoadImage(path)
    def LoadImage(self, path):
        try:
            self.path = path
            self.im = Image.open(path)
            self.width, self.height = self.im.size
            self.cubeWidth = int(self.width / self.cubeSize)
            self.cubeHeight = int(self.height / self.cubeSize)
        except Exception as e:
            print "Error when load image:", path
            print e
            exit(1)
    def GetBox(self, target, start, end, direction):
        if direction.lower() == 'row':
            box = (start * self.cubeSize,
                    target * self.cubeSize,
                    end * self.cubeSize ,
                    (target + 1) * self.cubeSize)
        elif direction.lower() == 'col':
            box = (target * self.cubeSize,
                    start * self.cubeSize,
                    (target + 1) * self.cubeSize,
                    end * self.cubeSize)
        else:
            raise Exception('Direction ' + str(direction)+ ' is unknown')
        return box
    def Row(self, rowNum, steps):
        assert(rowNum < self.height)
        steps = steps % self.cubeWidth
        firstBox = self.GetBox(rowNum, 0, self.cubeWidth - steps, 'row')
        firstIm = self.im.crop(firstBox)
        firstIm.load()
        lastBox = self.GetBox(rowNum, self.cubeWidth - steps, self.cubeWidth, 'row')
        lastIm = self.im.crop(lastBox)
        lastIm.load()

        self.im.paste(firstIm, (steps * self.cubeSize, rowNum * self.cubeSize))
        self.im.paste(lastIm, (0, rowNum * self.cubeSize))
    def Col(self, colNum, steps):
        assert(colNum < self.width)
        steps = steps % self.cubeHeight
        firstBox = self.GetBox(colNum, 0, self.cubeHeight - steps, 'col')
        firstIm = self.im.crop(firstBox)
        firstIm.load()
        lastBox = self.GetBox(colNum, self.cubeHeight - steps, self.cubeHeight, 'col')
        lastIm = self.im.crop(lastBox)
        lastIm.load()

        self.im.paste(firstIm, (colNum * self.cubeSize, steps * self.cubeSize))
        self.im.paste(lastIm, (colNum * self.cubeSize, 0))

    def Enc(self, key):
        key.PrepareEnc()
        for t in range(key.rollRound):
            for i in range(0, self.cubeHeight):
                self.Row(i, key.GetEncKey())
            for i in range(0, self.cubeWidth):
                self.Col(i, key.GetEncKey())
    def Dec(self, key):
        key.PrepareDec(self.cubeWidth + self.cubeHeight)
        for t in range(key.rollRound):
            for i in range(self.cubeWidth - 1, -1, -1):
                self.Col(i, -key.GetDecKey())
            for i in range(self.cubeHeight - 1, -1, -1):
                self.Row(i, -key.GetDecKey())
    def SmartProcess(self, key):
        if self.IsEnc(key):
            self.Dec(key)
        else:
            self.Enc(key)
    def IsEnc(self, key, printDetail = False):
        analyzer = PicAnalyzer(self.im, key.cubeSize)
        return analyzer.IsEnc(printDetail)
    def SaveImage(self, path = None):
        if path == None:
            path = self.path
        self.im.save(path, quality=85)
    def Show(self):
        print 'Show image'
        self.im.show()

class PicAnalyzer:
    def __init__(self, im, cubeSize = 8):
        self.im = im
        self.cubeSize = cubeSize
        self.width, self.height = im.size
    def GetDist(self, p1, p2):
        rgb1 = self.im.getpixel(p1)
        rgb2 = self.im.getpixel(p2)
        return ((rgb1[0]-rgb2[0])**2+(rgb1[1]-rgb2[1])**2+(rgb1[2]-rgb2[2])**2)**0.5
    def CountAvrStat(self):
        d_sum = 0
        count = 0
        d_square = 0
        d_square2 = 0
        for i in range(self.cubeSize/2, self.width-1, self.cubeSize):
            for j in range(self.cubeSize/2, self.height-1, self.cubeSize):
                d1 = self.GetDist((i,j), (i,j+1))
                d_sum += d1
                d_square += d1**2
                d2 = self.GetDist((i,j), (i+1,j))
                d_sum += d2
                d_square += d2**2
                count += 2
        self.avrDist = d_sum / count
        self.stdErr  = (d_square/count - (self.avrDist**2))**0.5
        return self.avrDist, self.stdErr
    def IsEnc(self, printDetail = False):
        self.CountAvrStat()
        d_square = 0
        count = 0
        for i in range(self.cubeSize, self.width, self.cubeSize):
            for j in range(self.cubeSize, self.height, self.cubeSize):
                d_square += self.GetDist((i, j), (i-1, j))**2
                d_square += self.GetDist((i, j), (i, j-1))**2
                count += 2
        stdErr = (d_square/count - self.avrDist**2)**0.5
        if printDetail:
            print "Average", self.avrDist
            print "Standard Error, ", self.stdErr
            print "Sample Std Error, ", stdErr
        return stdErr > self.stdErr*3 or \
                (stdErr > self.stdErr*2 and self.avrDist > 20)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--gen_key', action='store_true')
    parser.add_argument('--num', type=int, default=100)
    parser.add_argument('--size', type=int, default=8, dest='cubeSize')
    parser.add_argument('--round', type=int, default=4, dest='rollRound')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--key')
    parser.add_argument('--enc', action='store_true')
    parser.add_argument('--dec', action='store_true')
    parser.add_argument('--output_dir')
    parser.add_argument('--copy', action='store_true')
    parser.add_argument('path', nargs='*')
    options = parser.parse_args()

    if options.gen_key == True:
        k = Key(cubeSize = options.cubeSize, rollRound = options.rollRound)
        k.GenKey(options.num)
        if os.path.exists('./key') and options.force == False:
            print "We already have a key in this folder!"
        else:
            k.SaveKey('key')
    elif len(options.path) > 0:
        if options.key != None:
            keyPath = options.key
        else:
            keyPath = 'key'
        if os.path.exists(keyPath):
            k = Key().LoadKey(keyPath)
        else:
            print "Fail to load key", options.key, ", file does not exist"

        procesList = []
        for p in options.path:
            if os.path.exists(p):
                if os.path.isfile(p):
                    processList.append([p, p])
                elif os.path.isdir(p):
                    for item in os.listdir(p):
                        absPath = os.path.join(p, item)
                        if os.path.isfile(absPath):
                            procesList.append([absPath, absPath])
        if options.output_dir != None:
            if os.path.isdir(options.output_dir):
                for item in procesList:
                    item[1] = options.output_dir + os.path.basename(item[0])
        if options.copy == True:
            for item in procesList:
                lst = os.path.basename(item[1])
                item[1] = os.path.dirname + ".".join(lst[:-1])+'_copy.'+lst[-1]
        for item in procesList:
            try:
                c = Cube(item[0])
                if options.enc:
                    c.Enc(k)
                elif options.dec:
                    c.Dec(k)
                else:
                    c.SmartProcess(k)
                c.SaveImage(item[1])
                print "Success,", item[0]
            except Exception as e:
                print "We can't process", p
                print e
