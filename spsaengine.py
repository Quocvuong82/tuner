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
import random


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
        
        #the wanted values
        self.shared_delta={}
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
            line={}        
            for (k,v) in dict.items():
                k = k.strip()
                v = v.strip()
                if k != 'name':               
                   line[k] = float(v)
                else:
                   line[k] = v            
                
                
            self.variables.append(line)
        print(self.variables) 

        for line in self.variables:
            line['c'] = line['c_end']*int(self.settings['iterations'])**float(self.settings['Gamma'])
            line['a_end'] = line['r_end']*line['c_end']**2
            line['a'] = line['a_end']*(float(self.settings['A']) + float(self.settings['iterations']))**float(self.settings['Alpha'])
            
            self.shared_delta[line['name']] = float(line['init']);
            print(line)
                            
    def readconfig(self):
        with open(self.config_file, 'rt') as file:
            line=file.readline()
            while line != '':
                line = line.strip(' \r\n')
                
                elems=line.split('=')
                print(line)              
                if self.settings.has_key(elems[0]):
                    self.settings[elems[0]]=elems[1]
                print('read: ' + line)
                line=file.readline()
             
    def init_engine(self):
        self.tuner1 = Popen(self.settings['engine1'], stdin = PIPE, stdout = PIPE)
        self.tuner2 = Popen(self.settings['engine2'], stdin = PIPE, stdout = PIPE) 

        print("send uci to eng1")
        self.tuner1.stdin.write('uci\n')
        line=self.tuner1.stdout.readline()
        line.strip()
        while line.find('uciok') == -1:
            print(line)
            line=self.tuner1.stdout.readline()
            line.strip()
        print(line)
        
        print("send uci to eng2")        
        self.tuner2.stdin.write('uci\n')
        line=self.tuner2.stdout.readline()
        line.strip()
        while line.find('uciok') == -1:
            print(line)
            line=self.tuner2.stdout.readline()
            line.strip()
        print(line)            
                
    def init(self):
        self.readconfig()
        self.readvariable()
        self.readopenbook()
       
    def playgame(self, var_eng1, var_eng2):
        #return -1#int(random.uniform(-2, 2))
        for (k,v) in var_eng1.items():
            if var_eng1[k] > var_eng2[k]:
                return 1
            else:
                return -1

    def run_spsa(self):
        
        iter = 0;
        
        #init engine
        self.init_engine()

        while True:
            iter = iter+1
            if iter > int(self.settings['iterations']):
                return
            alpha = float(self.settings['Alpha'])
            gamma =  float(self.settings['Gamma'])
            A = float(self.settings['A']) 

            var_value={}
            var_min={}
            var_max={}
            var_a={}
            var_c={}
            var_R={}
            var_delta={}
            var_eng1={}
            var_eng2={}            
            for row in self.variables:
                name = row['name']
                
                value = self.shared_delta[name]
                min_v = float(row['min'])
                max_v = float(row['max'])
                a   = row['a']/(A + iter)**alpha
                c   = row['c']/iter**gamma
                R   = a/c**2
                
                delta = 1
                if int(random.uniform(0, 2)) != 0:
                    delta = 1
                else:
                    delta = -1               
                
                eng1 = min(max(value + c*delta, min_v), max_v)
                eng2 = min(max(value - c*delta, min_v), max_v)
                
                var_value[name]= value
                var_min[name]  = min_v 
                var_max[name]  = max_v
                var_a[name]    = a
                var_c[name]    = c
                var_R[name]    = R
                var_delta[name]= delta
                var_eng1[name] = eng1
                var_eng2[name] = eng2
                
                print("iteration:%d, variable:%s, value:%f, a:%f, c:%f, R:%f"%(iter, name, value, a, c, R))

            result =  self.playgame(var_eng1, var_eng2)
            
            print("iteration: %d"%iter)
            for row in self.variables:
                
                name = row['name']
                
                self.shared_delta[name] += var_R[name]*var_c[name]*result/var_delta[name]
                self.shared_delta[name] = max(min(self.shared_delta[name], var_max[name]), var_min[name])                

                print(self.shared_delta[name]),
            print('\n')
def main():
    
    os.chdir(os.path.dirname(sys.argv[0]))
    
    spsa = SPSAEngine()
    spsa.init()
    spsa.run_spsa()

if __name__=='__main__':
    main()
    