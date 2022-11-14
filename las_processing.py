import math
import os

import lasio
import matplotlib.pyplot as plt
from dtw import *
from scipy.ndimage import zoom
import time
import pandas as pd
from data_to_excel import data_to_excel
import numpy as np
np.seterr(divide='ignore', invalid='ignore')


def setup_parser(setup_path):
    with open(setup_path) as setup_file:
        setups = dict()
        for line in setup_file:
            k,v = line.split(' = ')
            setups[k] = v.split('\n')[0]
        return setups

def change_setups(setup_path):
    with open(setup_path, 'w') as file:
        try:
            file.write(f'LAS_FOLDER = '+input('Папка с las-файлами ')+'\n')
            file.write('DIST_THRESHOLD = '+input('Порог поиска (flaot) ')+'\n')
            file.write('MIN_STRETCH = '+input('Минимальное сжатие % (int) ')+'\n')
            file.write('MAX_STRETCH = '+input('Максимальное растяжение % (int) ')+'\n')
            file.write('STRETCH_STEP = '+input('Шаг растяжения % (int) ')+'\n')
            file.write('MODE = ' + input('Режим обработки шаблона: 0 - прямой; 1 - обратный; 2 - оба ') + '\n')
        except:
            print('Ошибка')


class LasData:
    def __init__(self, DataDir, t, min_stretch, max_stretch, stretch_step, mode):
        self.target_depth = None
        self.pattern_depth =None
        self.pattern = None
        self.target = None
        self.DataDir = DataDir
        self.intervals = []
        self.threshold = t
        self.min_stretch = min_stretch
        self.max_stretch = max_stretch
        self.stretch_step = stretch_step
        self.mode = mode

    def select_target_las(self):
        print('\n###########')
        if not os.listdir(self.DataDir):
            print('Не найдены файлы в папке for_LAS_FILES')
            return '---'
        for count,file in enumerate(os.listdir(self.DataDir)):
            print(f'{count+1}) {file}')
        print('###########')
        while True:
            try:
                SelectedFile = int(input('Выберите целевой файл: '))
                las = lasio.read(f'{self.DataDir}/{os.listdir(self.DataDir)[SelectedFile-1]}')
                print(f'{os.listdir(self.DataDir)[SelectedFile-1]} Выбран как целевой')
                break
            except (FileNotFoundError, PermissionError, TypeError, ValueError, IndexError):
                print('Ошибка. Попробуйте снова')

        curves = dict()
        self.target_depth = las.sections['Curves'][0]
        for count, curve in enumerate(las.sections['Curves'][1:]):
            print(f'{count + 1}) {curve.mnemonic} ({curve.descr})')
            curves[count + 1] = curve

        while True:
            try:
                SelectedCurve = int(input('Выберите кривую: '))
                self.target = curves[SelectedCurve]
                break
            except (KeyError, ValueError):
                print('Ошибка. Попробуйте снова\n')
        return os.listdir(self.DataDir)[SelectedFile-1]

    def select_pattern_las(self):
        print('\n###########')
        if not os.listdir(self.DataDir):
            print('Не найдены файлы в папке for_LAS_FILES')
            return '---'
        for count,file in enumerate(os.listdir(self.DataDir)):
            print(f'{count+1}) {file}')
        print('###########')
        while True:
            try:
                SelectedFile = int(input('Выберите шаблон: '))
                las = lasio.read(f'{self.DataDir}/{os.listdir(self.DataDir)[SelectedFile-1]}')
                print(f'{os.listdir(self.DataDir)[SelectedFile - 1]} Выбран как шаблон')
                break
            except (FileNotFoundError, PermissionError, TypeError, ValueError, IndexError):
                print('Ошибка. Попробуйте снова\n')

        curves = dict()
        self.pattern_depth = las.sections['Curves'][0]
        if self.target.mnemonic in las.sections['Curves']:
            choice = input(f'Хотите выбрать ту же кривую ({self.target.mnemonic})? [y/n]: ').lower()
            if choice == 'y':
                self.pattern = las.sections['Curves'][self.target.mnemonic]
            else:
                for count, curve in enumerate(las.sections['Curves'][1:]):
                    print(f'{count + 1}) {curve.mnemonic} ({curve.descr})')
                    curves[count + 1] = curve
                while True:
                    try:
                        SelectedCurve = int(input('Выберите кривую: '))
                        self.pattern = curves[SelectedCurve]
                        break
                    except (KeyError, ValueError, IndexError):
                        print('Ошибка. Попробуйте снова\n')
        return os.listdir(self.DataDir)[SelectedFile-1]

    def __alorithm(self,target,pattern,dcrit,min_stretch,max_stretch,step,mode):
        modes = {0: 'Прямой', 1: 'Обратный', 2: 'Прямой и обратный'}
        solutions = []
        min_dist = 100
        start_time = time.time()
        if mode == 1:
            pattern = -1 * pattern + 1
        for k in range(min_stretch, max_stretch + 1, step):
            patternN = pattern-min(pattern)
            patternN = zoom((patternN/ max(patternN)), k / 100)
            suspicious = []
            last_selected = 0
            IsSuspicious = False
            step_start_time = time.time()
            for num in range(len(target) - len(patternN)):
                try:
                    targetN = target[num:num + len(patternN)]-min(target[num:num + len(patternN)])
                    targetN = targetN/max(targetN)
                    dtw_step = dtw(targetN, patternN, keep_internals=True, step_pattern=symmetric1)
                    if dtw_step.distance < min_dist:
                        min_dist = dtw_step.distance
                    if dtw_step.distance < dcrit and not IsSuspicious:
                        IsSuspicious = True
                        last_selected = num
                        suspicious.append([dtw_step.distance, k / 100, num, dtw_step])
                    elif num - last_selected < len(patternN) and IsSuspicious:
                        suspicious.append([dtw_step.distance, k / 100, num, dtw_step])
                    elif IsSuspicious:
                        solutions.append(sorted(suspicious)[0])
                        suspicious = []
                        IsSuspicious = False
                        print(f'{solutions[-1][1]} - {solutions[-1][0]}')
                    else:
                        suspicious = []
                except (ValueError,RuntimeWarning):
                    dist = 0
            print(f'Time for {k / 100}: {time.time() - step_start_time}')
        print(f'###########################################\n'
              f'Общее время составило: {time.time() - start_time} ({modes[mode]})')
        print(f'Лучшее соответствие составило: {min_dist} ({modes[mode]})\n'
              f'###########################################')

        solutions_sorted = sorted(solutions)
        for i in range(len(solutions_sorted)):
            self.intervals.append(
                [solutions_sorted[i][2], solutions_sorted[i][2] + round(len(pattern) * solutions_sorted[i][1]),
                 solutions_sorted[i][0], solutions_sorted[i][3], mode, solutions_sorted[i][1]])
        # itervals [a, b, distance, dtw, reverse?, k]

    def find_patterns(self):
        modes = {0:'Прямой', 1:'Обратный', 2:'Прямой и обратный'}
        if not self.pattern == None and not self.target == None:
            pattern = self.pattern.data
            target = self.target.data
        else:
            print('Сначала выберите целевой файл и шаблон')
            return 0
        self.intervals.clear()
        print('Хотите использовать настройки по-умолчанию?\n'
              f'Порог поиска: {self.threshold}\n'
              f'Минимальное сжатие шаблона: {self.min_stretch}%\n'
              f'Максимальное растяжение шаблона: {self.max_stretch}%\n'
              f'Шаг растяжения {self.stretch_step}%\n'
              f'Режим обработки шаблона: ' + modes[self.mode])

        choice = input('[y/n]: ').lower()
        if choice == 'y':
            dcrit = float(self.threshold)
            min_stretch = int(self.min_stretch)
            max_stretch = int(self.max_stretch)
            step = int(self.stretch_step)
            mode = int(self.mode)
        else:
            dcrit = float(input('Выберите попрог поиска: '))
            min_stretch = int(input('Выберите минимальное сжатие шаблона (рекомендуемо от 1 до 100)%: '))
            max_stretch = int(input('Выберите максималное растяжение шаблона (рекомендуемо от 100 до 200)%: '))
            step = int(input('Выберите шаг растяжения (рекомендуемо 10)%: '))
            mode = int(input('Режим обработки шаблона (0 - прямой; 1 - обратный; 2 - оба): '))

        if mode == 2:
            self.__alorithm(target, pattern, dcrit, min_stretch, max_stretch, step, 0)
            self.__alorithm(target, pattern, dcrit, min_stretch, max_stretch, step, 1)
        else:
            self.__alorithm(target, pattern, dcrit, min_stretch, max_stretch, step, mode)
        i = 0
        while True:
            try:
                if i+1 < len(self.intervals):
                    if abs(self.intervals[i][0]-self.intervals[i+1][0])<(len(pattern)/2):
                        self.intervals.pop(i+1)
                    else:
                        i = i+1
                else:
                    break
            except:
                break
        return dcrit

    def plot_intervals(self,nplots):
        for interval in self.intervals[:nplots]:
            plt.figure(figsize=(10, 15))
            plt.subplot(1, 2, 1)
            targetN= self.target.data[interval[0]:interval[1]]-min(self.target.data[interval[0]:interval[1]])
            targetN = targetN/max(targetN)
            plt.plot(targetN,
                     'r', label=f'Целевая кривая')
            if interval[4] == 0:
                patternN = self.pattern.data - min(self.pattern.data)
                patternN = zoom((patternN / max(patternN)), interval[5])
                plt.plot(patternN,
                         linestyle='dashed', label=f'Шаблон Прямой')
            elif interval[4] == 1:
                patternN = -1*self.pattern.data+1
                patternN = patternN - min(patternN)
                patternN = zoom((patternN / max(patternN)), interval[5])
                plt.plot(patternN,
                         linestyle='dashed', label=f'Шаблон Обратный')
            plt.legend()

            plt.subplot(1, 2, 2)
            plt.plot(self.target.data, self.target_depth.data)
            plt.plot(self.target.data[interval[0]:interval[1]],
                     self.target_depth.data[interval[0]:interval[1]],
                     label=f'{interval[2]}')
            plt.gca().invert_yaxis()
            plt.ylabel('Depth[m]')
            plt.xlabel(f'{self.target.mnemonic}[{self.target.unit}]')
            plt.legend()
        plt.show()

    def convert_to_dataframe(self):
        modes = {0: 'Прямой', 1: 'Обратный', 2: 'Прямой и обратный'}
        l1=[]
        l2=[]
        l3=[]
        l4=[]
        l5=[]
        l6=[]
        for interval in self.intervals:
            l1.append(self.target_depth.data[interval[0]])
            l2.append(self.target_depth.data[interval[1]])
            l3.append(self.target_depth.data[interval[0]]-self.pattern_depth.data[0])
            l4.append(interval[2])
            l5.append((modes[interval[4]]))
            l6.append(interval[5]*100)
        df = pd.DataFrame({'Начало интервала':l1,
                           'Конец интервала':l2,
                           'Сдвиг относительно шаблона':l3,
                           'd':l4,
                           'Режим обработки шаблона':l5,
                           'Растяжение/сжатие шаблона %':l6})
        print(df)
        return df


def main():
    target_file = '---'
    pattern_file = '---'
    try:
        setups = setup_parser('LasProcessingSetups.txt')
        Data = LasData(setups['LAS_FOLDER'],
                   float(setups['DIST_THRESHOLD']),
                   int(setups['MIN_STRETCH']),
                   int(setups['MAX_STRETCH']),
                   int(setups['STRETCH_STEP']),
                   int(setups['MODE']))
    except (KeyError,ValueError):
        print('Ошибка в файле настроек')
        return 0
    while True:
        try:
            print('###########################################\n'
                  f'Выбранный целевой файл: {target_file}\n'
                  f'Выбранный файл шаблона: {pattern_file}\n'
                  '###########################################\n'
                  '1)Выбрать целевой las-файл\n'
                  '2)Выбрать шаблон\n'
                  '3)Найти подходящие интервалы\n'
                  '4)Построить графики\n'
                  '5)Изменить стандартные настройки\n'
                  '0)Выход\n'
                  '###########################################')
            action = int(input('Выберите действие: '))
            if action == 1:
                target_file = Data.select_target_las()
            elif action == 2:
                pattern_file = Data.select_pattern_las()
            elif action == 3:
                d = Data.find_patterns()
                #plot_intervals принеимает максимум выводимых графиков
                Data.plot_intervals(10)
                df = Data.convert_to_dataframe()
                tn,te = target_file.split('.')
                pn,pe = pattern_file.split('.')
                if not os.path.exists('Report'):
                    os.makedirs('Report')
                data_to_excel(df,f'Report/D_{round(d)}_{tn}_{pn}')
            elif action == 4:
                Data.plot_intervals(10)
            elif action == 5:
                change_setups('LasProcessingSetups.txt')
                choice = input('!!!Настройки будут применены после перезапуска!!!\n'
                      'Хотите перезапустить сейчас? [y/n]: ').lower()
                if choice == 'y':
                    print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n\n\n\n')
                    break
                else:
                    print('!!!Настройки будут применены после перезапуска!!!')
            elif action == 0:
                return 0
            else:
                print('---')
        except (ValueError):
            print('Ошибка')


if __name__ == '__main__':
    while True:
        exit = main()
        if exit == 0:
            break
