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
import datetime


class SPSAEngine:

    def __init__(self):
    
        self.config_file='./config.cfg'
        
        self.settings={\
        'variables':'./engine.var',\
        'log':'./log',\
        'gamelog':'./game',
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
        'winmovelimit':8,\
        'result':'./result'}
        
        self.tuner1=None
        self.tuner2=None
        
        self.variables=[]
        self.openbooks=[]
        
        #the wanted values
        self.shared_delta={}
        
        #log
        self.logfile = None
        self.gamefile= None
        
        self.resultfile = None        

    def __del__(self):
        if self.tuner1 != None:
           self.tuner1.kill() 
        if self.tuner2 != None:
           self.tuner2.kill() 
        if self.logfile != None:
           self.logfile.close()
        if self.gamefile != None:
           self.gamefile.close()
        if self.resultfile != None:
           self.resultfile.close()
    def log(self, line):
        if self.logfile is None:
            name = './%s-%s.log'%(self.settings['log'], time.strftime('%Y-%m-%d-%H-%M-%S',time.localtime()))
            self.logfile = open(name, 'wt')
        
        nowtime = time.strftime('%Y-%m-%d-%H:%M:%S',time.localtime())
        text = '[%s]:%s\n'%(nowtime, line)        
        self.logfile.write(text)
        self.logfile.flush()            
    def gamelog(self, line):
        if self.gamefile is None:
            name = './%s-%s.log'%(self.settings['gamelog'], time.strftime('%Y-%m-%d-%H-%M-%S',time.localtime()))
            self.gamefile = open(name, 'wt')
        
        nowtime = time.strftime('%Y-%m-%d-%H:%M:%S',time.localtime())
        text = '[%s]:%s\n'%(nowtime, line)        
        self.gamefile.write(text)
        self.gamefile.flush()
    def logresult(self, iter):
    
            if self.resultfile is None:
                name = './%s-%s.log'%(self.settings['result'], time.strftime('%Y-%m-%d-%H-%M-%S',time.localtime()))
                self.resultfile = open(name, 'wt')
                
            nowtime = time.strftime('%Y-%m-%d-%H:%M:%S',time.localtime())
            self.resultfile.write('[%s]: iter %d--------------------------------------------------------------------\n'%(nowtime, iter))
            self.resultfile.write('name,   init,  max,  min,  c_end,  r_end,  elod\n')
            
            for row in self.variables:
                
                name = row['name']                

                delataline = '%s, %f, %f, %f, %f, %f, %f\n'%(name, self.shared_delta[name], row['max'],row['min'], row['c_end'], row['r_end'], row['elod'])               
                
                self.resultfile.write(delataline)               
            
            self.resultfile.flush()       

                        
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
                line = line.strip(' \r\n[]')                
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
        
        result = 0
        
        #select a opening   
        fen = 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1'
        fenindex = 0
        if len(self.openbooks) > 0:       
            fenindex = random.randint(0, len(self.openbooks)-1)
            fen = self.openbooks[fenindex]
            
        temparray=fen.split(' ')
        
        side_to_start = temparray[1]
        
        #set value to engine
        for (k, v) in  var_eng1.items():
            var1 = int(var_eng1[k])
            var2 = int(var_eng2[k])
            
            command = 'setoption name %s value %d\n'%(k, var1)
            self.tuner1.stdin.write(command)
            
            command = 'setoption name %s value %d\n'%(k, var2)
            self.tuner2.stdin.write(command)
         
                
        #play two game
        for eng1_is_white in range(2):
            self.tuner1.stdin.write('ucinewgame\n')
            self.tuner2.stdin.write('ucinewgame\n')
            
            self.tuner1.stdin.write('isready\n')
            self.tuner2.stdin.write('isready\n')
            
            line=self.tuner1.stdout.readline()            
            while line.find('readyok') == -1:                
                line=self.tuner1.stdout.readline()               
                
            line=self.tuner2.stdout.readline()
            while line.find('readyok') == -1:
                line=self.tuner2.stdout.readline()             
            
            eng1_time = int(self.settings['basetime'])
            eng2_time = int(self.settings['basetime'])
            
            engine_to_move = 1;
            if (eng1_is_white==1 and side_to_start=='w') or (eng1_is_white==0 and side_to_start=='b'):
                engine_to_move = 1
            else:
                engine_to_move = 2
                
            self.gamelog('Starting game using opening fen%d :%s .Engine to start:%d'%(fenindex,fen, engine_to_move))
            
            #init game variabless
            moves=''
            winner=None
            draw_counter=0
            win_counter=[0,0,0]
            move_iter = 0 
            while True:
                wtime =  eng1_time if  eng1_is_white == 1 else  eng2_time
                btime =  eng1_time if  eng1_is_white == 0 else  eng2_time
                
                current_write_turner = self.tuner1.stdin if engine_to_move == 1 else self.tuner2.stdin
                current_read_turner  = self.tuner1.stdout if engine_to_move == 1 else  self.tuner2.stdout
                
                #send engine current position
                command = 'position fen %s \n'%(fen)
                if moves != '':
                    command = 'position fen %s moves %s\n'%(fen, moves)
                print('send command %s'%command)
                current_write_turner.write(command)
                
                time = eng1_time if engine_to_move==1 else eng2_time
                
                self.gamelog('Engine %d starts thinking. Time: %d. Moves: %s'%(engine_to_move, time, moves))
                self.gamelog('position fen %s moves%s'%(fen, moves))
                print('engine %d starts thinking Time: %d moves %s\n'%(engine_to_move, time, moves)) 
                
                #step: let it go
                inctime = int(self.settings['inctime'])
                t0 = datetime.datetime.now()
                command = 'go wtime %d btime %d winc %d binc %d\n'%(wtime, btime, inctime,inctime) 
                print('send command %s'%command)
                current_write_turner.write(command)

                score = 0
                flag_mate = 0
                flag_stalemate = 0 

                revline = current_read_turner.readline()
                while revline != '':
                    revline = revline.strip(' \r\n')
                    array = revline.split(' ')
                    if len(array) > 0 and array[0] == 'bestmove':
                        if array[1].find('none') != -1:
                            flag_stalemate = 1
                        moves = moves + ' ' + array[1]
                        break

                    for index,elem in enumerate(array):
                        if elem == 'mate' and array[index+1] == '1':
                            flag_mate = 1
                            winner = engine_to_move

                    for index,elem in enumerate(array): 
                        if elem == 'score':
                            if array[index+1] =='cp':
                                score = int(array[index+2])
                            elif array[index+1] =='mate':
                                score = +100000 if int(array[index+2])>0 else -100000                                
                            else:
                                score = int(array[index+1])
                            #print('score %d'%score)                    
                                        
                    revline = current_read_turner.readline()
                
                self.gamelog("Score: %s"%(score,))                
                print('score:%d'%score) 
                
                elapsed = datetime.datetime.now() - t0
                elapsedtime = elapsed.seconds
                
                if engine_to_move == 1:
                    eng1_time = eng1_time - elapsedtime + inctime
                
                if engine_to_move == 2:
                    eng2_time = eng2_time - elapsedtime + inctime
        
        
                #check for mate and stalemate
                if flag_mate == 1:
                    winner = engine_to_move
                    break
        
                if flag_stalemate == 1:
                    winner = 1 if engine_to_move == 2 else 2
                    break
                    
                #Update draw counter
                draw_counter = draw_counter + 1 if abs(score) <= int(self.settings['drawscorelimit']) else 0
               
                print("draw counter: %d/%d"%(draw_counter, int(self.settings['drawmovelimit'])))
                self.gamelog('Draw counter: %d/%d'%(draw_counter, int(self.settings['drawmovelimit'])))
                
                
                if draw_counter > int(self.settings['drawmovelimit']):
                    winner = 0
                    break
                    
                us = engine_to_move
                them = 2 if engine_to_move==1 else 1
                
                win_counter[us] = win_counter[us] + 1 if score >= int(self.settings['winscorelimit']) else 0
                win_counter[them]= win_counter[them] + 1 if score <= -int(self.settings['winscorelimit']) else 0
                
                
                
                if win_counter[us] > 0:
                    print('Win Counter: %d/%d'%(win_counter[us], int(self.settings['winmovelimit'])))
                    self.gamelog('Win Counter: %d/%d'%(win_counter[us], int(self.settings['winmovelimit'])))
                    
                if win_counter[them] > 0:
                    print('Loss Counter: %d/%d'%(win_counter[them], int(self.settings['winmovelimit'])))
                    self.gamelog('Loss Counter: %d/%d'%(win_counter[them], int(self.settings['winmovelimit'])))
                
                
                if win_counter[us] > int(self.settings['winmovelimit']):
                     winner = us
                     break
                     
                if win_counter[them] > int(self.settings['winmovelimit']):
                     winner = them
                     break
                
                move_iter += 1;
                #draw
                if  move_iter>160:
                    winner = 0
                    break                    
                #change turn
                engine_to_move = them
            
            #record the result
            self.gamelog('Winner: %s'%(winner,))            
            print('winner: %d'%winner) 
             
            if winner == 1:
                result += 1
            elif winner == 2:
                result -= 1
            else:
                result += 0            
        
        return result    
            
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
            
            delataline = ''
            for row in self.variables:
                
                name = row['name']
                
                self.shared_delta[name] += var_R[name]*var_c[name]*result/var_delta[name]
                self.shared_delta[name] = max(min(self.shared_delta[name], var_max[name]), var_min[name])                
                
                delataline = delataline + ' ' + name +':' + str(self.shared_delta[name])
                #print(self.shared_delta[name]),
            #print('\n')
            
            logline = '%d: %s'%(iter, delataline)
            self.log(logline)
            
            if iter%1==0:
               self.logresult(iter);
                
def main():
    
    os.chdir(os.path.dirname(sys.argv[0]))
    
    spsa = SPSAEngine()
    spsa.init()
    spsa.run_spsa()

if __name__=='__main__':
    main()
    