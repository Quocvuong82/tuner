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

class GameMatch:
    def __init__(self):
    
       self.engine1_var='./eng1.var'
       self.engine2_var='./eng2.var'
    
       self.engine1='./engine1.exe'
       self.engine2='./engine2.exe' 

       self.openbook='./openbook.epd'
       self.openbooks=[]       
       
       self.mathiter = 10
       
       #win draw loss count
       self.eng1_result=[0,0,0]
       self.eng2_result=[0,0,0]
    
       self.eng1_option=[]
       self.eng2_option=[]
       
       self.tuner1=None
       self.tuner2=None
       
       #log
       self.logfile = None
       self.gamefile= None
       
       self.settings={\
        'log':'./matchlog',\
        'gamelog':'./matchgamelog',\
        'epdbook':'./openbook.epd',\
        'basetime':1000,\
        'inctime':50,\
        'drawscorelimit':4,\
        'drawmovelimit':8,\
        'winscorelimit':650,\
        'winmovelimit':8,\
        'result':'./result'}
        
    def __del__(self):
        if self.tuner1 != None:
           self.tuner1.kill() 
        if self.tuner2 != None:
           self.tuner2.kill() 
        if self.logfile != None:
           self.logfile.close()
        if self.gamefile != None:
           self.gamefile.close()
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
    def readopenbook(self):
        with open(self.settings['epdbook'],'rt') as file:
            for line in file:
                line=line.strip()
                if line != '':
                    self.openbooks.append(line)
                    print(line)
    def readconfig(self):
        for dict in csv.DictReader(open(self.engine1_var,"rb")):
            line={}        
            for (k,v) in dict.items():
                k = k.strip()
                v = v.strip()
                if k != 'name':               
                   line[k] = float(v)
                else:
                   line[k] = v            
                
                
            self.eng1_option.append(line)
         
        for dict in csv.DictReader(open(self.engine2_var,"rb")):
            line={}        
            for (k,v) in dict.items():
                k = k.strip()
                v = v.strip()
                if k != 'name':               
                   line[k] = float(v)
                else:
                   line[k] = v            
                
                
            #self.eng2_option.append(line)
    def init_engine(self):
        self.tuner1 = Popen(self.engine1, stdin = PIPE, stdout = PIPE)
        self.tuner2 = Popen(self.engine2, stdin = PIPE, stdout = PIPE) 

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
        self.readopenbook()        
    def run_play(self):
        iter = 0;
        
        #init engine
        self.init_engine()

        while True:
            iter = iter+1
            if iter > int(self.mathiter):
                return 
                
            var_eng1={}
            var_eng2={} 

            for row in self.eng1_option:
                name = row['name']                
                value = row['init']
                var_eng1[name] = value
                
            for row in self.eng2_option:
                name = row['name']                
                value = row['init']
                var_eng2[name] = value
                
            result =  self.playgame(var_eng1, var_eng2)
            
            print("iteration: %d"%iter)      

            
            logline = 'iter %d, result %d'%(iter, result)
            self.log(logline)
            
            if result == 0:            
               self.eng1_result[1] +=1
               self.eng2_result[1] +=1
               
               
            if result == 1:            
               self.eng1_result[0] +=1
               self.eng2_result[2] +=1
            if result == 2:            
               self.eng1_result[0] +=2
               self.eng2_result[2] +=2               

            if result == -1:            
               self.eng1_result[2] +=1
               self.eng2_result[0] +=1
            if result == -2:            
               self.eng1_result[2] +=2
               self.eng2_result[0] +=2
               
            text = 'eng1 win %d/%d draw %d/%d loss %d/%d\n'%(self.eng1_result[0], iter*2, self.eng1_result[1], iter*2, self.eng1_result[2], iter*2)
            self.log(text)
            text = 'eng2 win %d/%d draw %d/%d loss %d/%d\n'%(self.eng2_result[0], iter*2, self.eng2_result[1], iter*2, self.eng2_result[2], iter*2)
            self.log(text)
    
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
            
            command = 'setoption name %s value %d\n'%(k, var1)
            self.tuner1.stdin.write(command)
        for (k, v) in  var_eng2.items():
            var2 = int(var_eng2[k])   
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
        
def main():
    
    os.chdir(os.path.dirname(sys.argv[0]))
    
    spsa = GameMatch()
    spsa.init()
    spsa.run_play()

if __name__=='__main__':
    main()   
    
    