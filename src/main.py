'''
Created on Mar 14, 2017

'''
import os

from XingProfilesReader import XingProfilesReader

def main():
    xingData = XingProfilesReader()
    xingData.dumpDataSet(os.getcwd() + '/' + 'xingData.pickle')

if __name__ == '__main__':
    main()