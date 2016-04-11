#!/usr/bin/python
from multiprocessing import cpu_count
from multiprocessing.managers import BaseManager
from subprocess import Popen, PIPE
from threading import Thread
import time
import urllib2
import os
import csv
import sys


class SPSAEngine:

    def __init__(self):
    
        self.config_file='./config.cfg'
        
        self.settings={\
        'variables':'./engine.var',\
        'log':'./engine.log',\
        'gamelog':'./engine_game_thread.log',
        'iterations':100,\
        'A':5000,\
        'Gamma':0.101,\
        'Alpha':0.602,\
        'engine1':'./challenger1.exe',\
        'engine2':'./challenger2.exe',\
        'epdbook':'./openbook.epd',\
        'basetime':1000,\
        'inctime':50,\
        'concurrency':1,\
        'drawscorelimit':4,\
        'drawmovelimit':8,\
        'winscorelimit':650,\
        'winmovelimit':8}
        
        self.tuner1=None
        self.tuner2=None
        
        self.variables=[]
        self.openbooks=[]
    def __del__(self):
        if self.tuner1 != None:
           self.tuner1.kill() 
        if self.tuner2 != None:
           self.tuner2.kill() 
        pass
    def readopenbook(self):
        with open(self.settings['epdbook'],'rt') as file:
            for line in file:
                line=line.strip()
                if line != '':
                    self.openbooks.append(line)
                    print(line)
    def readvariable(self):
        for dict in csv.DictReader(open(self.settings['variables'],"rb")):            
            for (k,v) in dict.items():
                k = k.strip()
                v = v.strip()
                t = {}
                t[k]=v
                #print(t)
                self.variables.append(t)
        print(self.variables)                
    def readconfig(self):
        with open(self.config_file, 'rt') as file:
            line=file.readline()
            while line != '':
                line = line.strip(' \r\n')                
                elems=line.split('=')
                if self.settings.has_key(elems[0]):
                    self.settings[elems[0]]=elems[1]
                print('read: ' + line)
                line=file.readline()
             
    def init_engine(self):
        self.tuner1 = Popen(self.settings['engine1'], stdin = PIPE, stdout = PIPE)
        self.tuner2 = Popen(self.settings['engine2'], stdin = PIPE, stdout = PIPE) 

        self.tuner1.stdin.write('uci\n')
        line=self.tuner1.stdout.readline()
        while line != 'uciok':
            print(line)
            line=self.tuner1.stdout.readline()
            
        self.tuner2.stdin.write('uci\n')
        line=self.tuner2.stdout.readline()
        while line != 'uciok':
            print(line)
            line=self.tuner2.stdout.readline()            
    def init(self):
        self.readconfig()
        self.readvariable()
        self.readopenbook()
        self.init_engine()
    def playgame(self):
        pass

    def run_spsa(self):
        pass    


def main():
    
    os.chdir(os.path.dirname(sys.argv[0]))
    
    spsa = SPSAEngine()
    spsa.init()
    spsa.run_spsa()

if __name__=='__main__':
    main()
    